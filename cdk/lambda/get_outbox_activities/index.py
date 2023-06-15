# -*- coding: utf-8 -*-

"""Returns activities in the outbox of a given user.

You have to specify the following environment variables:
* ``USER_TABLE_NAME``: name of the DynamoDB table that stores user information.
* ``OBJECT_TABLE_NAME``: name of the DynamoDB table that manages metadata and
  history of objects.
* ``OBJECTS_BUCKET_NAME``: name of the S3 bucket that stores objects.
* ``DOMAIN_NAME_PARAMETER_PATH``: path to the parameter storing the domain name
  in Parameter Store on AWS Systems Manager.

You may specify the following optional environment variable:
* ``PAGE_SIZE``: maximum number of activities in a single page. 20 by default.
"""

from itertools import islice
import logging
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple
import boto3
from libactivitypub.activity_streams import ACTIVITY_STREAMS_CONTEXT
from libmumble.exceptions import (
    BadRequestError,
    CorruptedDataError,
    NotFoundError,
)
from libmumble.object_table import (
    ActivityMetadata,
    ObjectTable,
    PrimaryKey,
    deserialize_activity_key,
    serialize_activity_key,
)
from libmumble.parameters import get_domain_name
from libmumble.user_table import User, UserTable
from libmumble.utils import urlencode


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

DOMAIN_NAME = get_domain_name(boto3.client('ssm'))

USER_TABLE_NAME = os.environ['USER_TABLE_NAME']
USER_TABLE = UserTable(boto3.resource('dynamodb').Table(USER_TABLE_NAME))

OBJECT_TABLE_NAME = os.environ['OBJECT_TABLE_NAME']
OBJECT_TABLE = ObjectTable(boto3.resource('dynamodb').Table(OBJECT_TABLE_NAME))

OBJECTS_BUCKET_NAME = os.environ['OBJECTS_BUCKET_NAME']

DEFAULT_PAGE_SIZE = 20
PAGE_SIZE = int(os.environ.get('PAGE_SIZE', DEFAULT_PAGE_SIZE))


def make_activity_collection_page(
    user: User,
    id: str, # pylint: disable=invalid-name, redefined-builtin
    activities: Sequence[Dict[str, Any]],
    options: Optional[Dict[str, Any]]=None,
) -> Dict[str, Any]:
    """Makes a ``dict`` that represents a collection page of given activities.

    ``options`` may include ``prev`` and ``next``.
    """
    if options is None:
        options = {}
    return {
        '@context': ACTIVITY_STREAMS_CONTEXT,
        'id': id,
        'type': 'OrderedCollectionPage',
        'partOf': user.outbox_uri,
        'orderedItems': activities,
        **options,
    }


def get_outbox_page(
    user: User,
    before: Optional[str]=None,
    after: Optional[str]=None,
) -> Tuple[List[ActivityMetadata], List[Dict[str, Any]]]:
    """Returns the page of activities in user's outbox.

    The first page is obtained if none of ``before`` and ``after`` is
    specified.

    :param Optional[str] before: obtains activities before this ID; i.e.,
    older activities.

    :param Optional[str] after: obtains activities after this ID; i.e., newer
    activities.

    :returns: tuple of metadata of activities, and a list of activities in
    ``dict`` representation. activities are chronologically ordered if
    ``after`` is specified, otherwise reverse-chronologically ordered.

    :raises ValueError: if both of ``before`` and ``after`` are provided,
    or if ``before`` is invalid,
    or if ``after`` is invalid.

    :raises TooManyAccessError: if there are too many requests.

    :raises CorruptedDataError: if any object cannot be resolved.
    """
    before_key: Optional[PrimaryKey] = None
    if before:
        before_key = deserialize_activity_key(before, user.username)
    after_key: Optional[PrimaryKey] = None
    if after:
        after_key = deserialize_activity_key(after, user.username)
    meta_activities = list(islice(
        OBJECT_TABLE.enumerate_user_activities(
            user,
            PAGE_SIZE,
            before=before_key,
            after=after_key,
        ),
        PAGE_SIZE,
    ))
    if after is not None:
        meta_activities.reverse() # → reverse-chronological
    s3_client = boto3.client('s3')
    try:
        return (
            meta_activities,
            [
                activity.resolve(s3_client, OBJECTS_BUCKET_NAME).to_dict()
                    for activity in meta_activities
            ],
        )
    except NotFoundError as exc:
        raise CorruptedDataError(f'{exc}') from exc


def get_first_outbox_page(user: User) -> Dict[str, Any]:
    """Returns the first page of the collection of activities in the outbox.

    :raises TooManyAccessError: if there are too many requests.
    """
    meta_activities, activities = get_outbox_page(user)
    current_id = f'{user.outbox_uri}?page=true'
    if len(activities) == 0:
        return make_activity_collection_page(user, current_id, [])
    next_key = urlencode(
        serialize_activity_key(meta_activities[-1].primary_key),
    )
    return make_activity_collection_page(user, current_id, activities, {
        'next': f'{user.outbox_uri}?page=true&before={next_key}',
    })


def get_outbox_page_before(user: User, before: str):
    """Returns the page of activities before a given ID in user's outbox.

    :raises ValueError: if ``before`` is invalid.

    :raises TooManyAccessError: if there are too many requests.
    """
    meta_activities, activities = get_outbox_page(user, before=before)
    before_key = urlencode(before)
    current_id = f'{user.outbox_uri}?page=true&before={before_key}'
    if len(activities) == 0:
        prev_key = urlencode(
            serialize_activity_key(
                ObjectTable.make_oldest_user_activity_key(user),
            ),
        )
        return make_activity_collection_page(user, current_id, [], {
            'prev': f'{user.outbox_uri}?page=true&after={prev_key}',
        })
    prev_key = urlencode(
        serialize_activity_key(meta_activities[0].primary_key),
    )
    next_key = urlencode(
        serialize_activity_key(meta_activities[-1].primary_key),
    )
    return make_activity_collection_page(user, current_id, activities, {
        'prev': f'f{user.outbox_uri}?page=true&after={prev_key}',
        'next': f'f{user.outbox_uri}?page=true&before={next_key}',
    })


def get_outbox_page_after(user: User, after: str):
    """Returns the page of activities after a given ID in user's outbox.

    :raises ValueError: if ``after`` is invalid.

    :raises TooManyAccessError: if there are too many requests.
    """
    meta_activities, activities = get_outbox_page(user, after=after)
    after_key = urlencode(after)
    current_id = f'{user.outbox_uri}?page=true&after={after_key}'
    if len(activities) == 0:
        return make_activity_collection_page(user, current_id, [], {
            'next': f'{user.outbox_uri}?page=true',
        })
    prev_key = urlencode(
        serialize_activity_key(meta_activities[0].primary_key),
    )
    next_key = urlencode(
        serialize_activity_key(meta_activities[-1].primary_key),
    )
    return make_activity_collection_page(user, current_id, activities, {
        'prev': f'{user.outbox_uri}?page=true&after={prev_key}',
        'next': f'{user.outbox_uri}?page=true&before={next_key}',
    })


def lambda_handler(event, _context):
    """Runs on AWS Lambda.

    ``event`` must be a ``dict`` similar to the following:

    .. code-block:: python

        {
            'username': '<username>',
            'page': True,
            'after': '<activity-id>',
            'before': '<activity-id>'
        }

    If ``page`` is ``False`` or omitted, returns a ``dict`` similar to the
    following:

    .. code-block:: python

        {
            '@context': 'https://www.w3.org/ns/activitystreams',
            'id': 'https://<domain-name>/users/<username>/outbox',
            'type': 'OrderedCollection',
            'first': 'https://<domain-name>/users/<username>/outbox?page=true'
        }

    If ``page`` is ``True``, returns a ``dict`` similar to the following:

    .. code-block:: python

        {
            '@context': 'https://www.w3.org/ns/activitystreams',
            'id': 'https://<domain-name>/users/<username/outbox?page=true>',
            'type': 'OrderedCollectionPage',
            'partOf': 'https://<domain-name>/users/<username>/outbox',
            'next': 'https://<domain-name>/users/<username>/outbox?page=true&before=xyz',
            'prev': 'https://<domain-name>/users/<username>/outbox?page=true&after=xyz',
            'orderedItems': [
                {}
            ]
        }

    ``after`` and ``before`` are optional.
    If none of ``after`` and ``before`` are specified, returns the first page.

    :raises KeyError: if ``event`` does not have "username".

    :raises BadRequestError: if both of ``after`` and ``before`` are specified.

    :raises NotFoundError: if the user does not exist.

    :raises TooManyAccessError: if there are too many requests.
    """
    LOGGER.debug('obtaining activities: %s', event)
    username = event['username']
    is_page = bool(event.get('page', False))
    after = event.get('after')
    before = event.get('before')
    if after is not None and before is not None:
        raise BadRequestError('both of after and before are specified')
    LOGGER.debug('looking up user: %s', username)
    user = USER_TABLE.find_user_by_username(username, DOMAIN_NAME)
    if user is None:
        raise NotFoundError(f'no such user: {username}')
    if not is_page:
        return {
            '@context': ACTIVITY_STREAMS_CONTEXT,
            'id': user.outbox_uri,
            'type': 'OrderedCollection',
            'first': f'{user.outbox_uri}?page=true',
        }
    if before is not None:
        try:
            return get_outbox_page_before(user, before)
        except ValueError as exc:
            raise BadRequestError(f'{exc}') from exc
    if after is not None:
        try:
            return get_outbox_page_after(user, after)
        except ValueError as exc:
            raise BadRequestError(f'{exc}') from exc
    return get_first_outbox_page(user)
