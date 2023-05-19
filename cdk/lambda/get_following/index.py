# -*- coding: utf-8 -*-

"""Returns accounts followed by a given user.

You have to specify the following environment variables:
* ``USER_TABLE_NAME``: name of the DynamoDB table that manages user information.
* ``DOMAIN_NAME_PARAMETER_PATH``: name of the parameter storing the domain name
  in Parameter Store on AWS Systems Manager.

You may specify the following optional environment variable:
* ``PAGE_SIZE``: maximum number of accounts included in a single collection
  page. 12 by default.
"""

from itertools import islice
import logging
import os
from typing import Any, Dict, List, Optional
import boto3
from libactivitypub.activity_streams import ACTIVITY_STREAMS_CONTEXT
from libmumble.exceptions import BadRequestError, NotFoundError
from libmumble.parameters import get_domain_name
from libmumble.user_table import User, UserTable
from libmumble.utils import urlencode


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

DEFAULT_PAGE_SIZE = 12
PAGE_SIZE = int(os.environ.get('PAGE_SIZE', DEFAULT_PAGE_SIZE))

DOMAIN_NAME = get_domain_name(boto3.client('ssm'))

USER_TABLE_NAME = os.environ['USER_TABLE_NAME']
USER_TABLE = UserTable(boto3.resource('dynamodb').Table(USER_TABLE_NAME))


def make_following_page(
    user: User,
    id: str, # pylint: disable=invalid-name, redefined-builtin
    followee_ids: List[str],
    options: Optional[Dict[str, Any]]=None,
) -> Dict[str, Any]:
    """Makes a collection page of specified accounts followed by a given user.
    """
    if options is None:
        options = {}
    return {
        '@context': ACTIVITY_STREAMS_CONTEXT,
        'id': id,
        'type': 'OrderedCollectionPage',
        'partOf': user.following_uri,
        'totalItems': user.following_count,
        'orderedItems': followee_ids,
        **options,
    }


def get_following_page(
    user: User,
    after: Optional[str]=None,
    before: Optional[str]=None,
) -> List[str]:
    """Obtains a collection page of accounts followed by a given user.

    :returns: list of up to ``PAGE_SIZE`` account IDs followed by a given user.

    :raises TooManyAccessError: if access to the DynamoDB table exceeds the
    limit.
    """
    return list(islice(
        user.enumerate_following(PAGE_SIZE, after=after, before=before),
        PAGE_SIZE,
    ))


def get_first_following_page(user: User) -> Dict[str, Any]:
    """Obtains the first collection page of accounts followed by a given user.

    :raises TooManyAccessError: if access to the DynamoDB table exceeds the
    limit.
    """
    current_id = f'{user.following_uri}?page=true'
    followee_ids = get_following_page(user)
    if len(followee_ids) == 0:
        return make_following_page(user, current_id, [])
    next_key = urlencode(followee_ids[-1])
    return make_following_page(user, current_id, followee_ids, {
        'next': f'{user.following_uri}?page=true&after={next_key}',
    })


def get_following_page_after(user: User, after: str) -> Dict[str, Any]:
    """Obtains the collection page of accounts followed by a given user after
    a specified ID.

    :raises TooManyAccessError: if access to the DynamoDB table exceeds the
    limit.
    """
    after_key = urlencode(after)
    current_id = f'{user.following_uri}?page=true&after={after_key}'
    followee_ids = get_following_page(user, after=after)
    if len(followee_ids) == 0:
        return make_following_page(user, current_id, [], {
            'prev': f'{user.following_uri}?page=true&before=~',
        })
    prev_key = urlencode(followee_ids[0])
    next_key = urlencode(followee_ids[-1])
    return make_following_page(user, current_id, followee_ids, {
        'prev': f'{user.following_uri}?page=true&before={prev_key}',
        'next': f'{user.following_uri}?page=true&after={next_key}',
    })


def get_following_page_before(user: User, before: str) -> Dict[str, Any]:
    """obtains the collection page of accounts followed by a given user before
    a specified ID.

    :raises TooManyAccessError: if access to the DynamoDB table exceeds the
    limit.
    """
    before_key = urlencode(before)
    current_id = f'{user.following_uri}?page=true&before={before_key}'
    followee_ids = get_following_page(user, before=before)
    if len(followee_ids) == 0:
        return make_following_page(user, current_id, [], {
            'next': f'{user.following_uri}?page=true',
        })
    prev_key = urlencode(followee_ids[0])
    next_key = urlencode(followee_ids[-1])
    return make_following_page(user, current_id, followee_ids, {
        'prev': f'{user.following_uri}?page=true&before={prev_key}',
        'next': f'{user.following_uri}?page=true&after={next_key}',
    })


def lambda_handler(event, _context):
    """Runs on AWS Lambda.

    ``event`` must be a ``dict`` similar to the following:

    .. code-block:: python

        {
            'username': '<username>',
            'page': True,
            'after': '<after-account-id>',
            'before': '<before-account-id>'
        }

    Returns a collection object similar to the following if ``page`` is
    ``False`` or omitted.

    .. code-block:: python

        {
            '@context': 'https://www.w3.org/ns/activitystreams',
            'id': 'https://<domain-name>/users/<username>/following',
            'type': 'OrderedCollection',
            'totalItems': 123,
            'first': 'https://<domain-name>/users/<username>/following?page=true'
        }

    Otherwise, returns a collection page object similar to the following:

    .. code-block:: python

        {
            '@context': 'https://www.w3.org/ns/activitystreams',
            'id': 'https://<domain-name>/users/<username>/following?page=true',
            'type': 'OrderedCollectionPage',
            'partOf': 'https://<domain-name>/users/<username>/following',
            'totalItems': 123,
            'orderedItems': [
                '<followee-id>',
            ],
            'next': 'https://<domain-name>/users/<username>/following?page=true&after=https%3A%2F%2Fmumble.codemonger.io%2Fusers%2Fkemoto',
            'prev': 'https://<domain-name>/users/<username>/following?page=true&after=https%3A%2F%2Fmumble.codemonger.io%2Fusers%2Fkemoto'
        }

    Returns the first page if ``page`` is ``True`` and neither of ``before``
    and ``after`` is specified.

    :raises KeyError: if ``event`` lacks any mandatory key.

    :raises NotFoundError: if the user does not exist in the user table.

    :raises BadRequestError: if both of ``before`` and ``after`` are specified.

    :raises TooManyRequestError: if access to the DynamoDB table exceeds the
    limit.
    """
    LOGGER.debug('obtaining following: %s', event)
    username = event['username']
    is_page = bool(event.get('page', False))
    after = event.get('after')
    before = event.get('before')
    if after is not None and before is not None:
        raise BadRequestError('both of "after" and "before" are specified')
    LOGGER.debug('resolving user: %s', username)
    user = USER_TABLE.find_user_by_username(username, DOMAIN_NAME)
    if user is None:
        raise NotFoundError(f'no such user: {username}')
    if not is_page:
        return {
            '@context': ACTIVITY_STREAMS_CONTEXT,
            'id': user.following_uri,
            'type': 'OrderedCollection',
            'totalItems': user.following_count,
            'first': f'{user.following_uri}?page=true',
        }
    if after is not None:
        return get_following_page_after(user, after)
    if before is not None:
        return get_following_page_before(user, before)
    return get_first_following_page(user)
