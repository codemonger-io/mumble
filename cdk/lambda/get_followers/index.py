# -*- coding: utf-8 -*-

"""Returns the followers of a given user.

You have to specify the following environment variables:
* ``USER_TABLE_NAME``: name of the DynamoDB table that stores user information.
* ``DOMAIN_NAME_PARAMETER_PATH``: path to the parameter containing the domain
  name in Parameter Store on AWS Systems Manager.

You may specify the following optional environment variables:
* ``PAGE_SIZE``: number of followers in a single page. 12 by default.
"""

from itertools import islice
import logging
import os
from typing import Any, Dict, Optional, Sequence
import boto3
from libactivitypub.activity_streams import ACTIVITY_STREAMS_CONTEXT
from libmumble.exceptions import BadRequestError, NotFoundError
from libmumble.parameters import get_domain_name
from libmumble.user_table import User, UserTable
from libmumble.utils import urlencode


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

DOMAIN_NAME = get_domain_name(boto3.client('ssm'))

USER_TABLE_NAME = os.environ['USER_TABLE_NAME']
USER_TABLE = UserTable(boto3.resource('dynamodb').Table(USER_TABLE_NAME))

DEFAULT_PAGE_SIZE = 12
PAGE_SIZE = int(os.environ.get('PAGE_SIZE', DEFAULT_PAGE_SIZE))


def make_follower_collection_page(
    user: User,
    id: str, # pylint: disable=invalid-name, redefined-builtin
    followers: Sequence[str],
    options: Optional[Dict[str, Any]]=None,
) -> Dict[str, Any]:
    """Makes an object of a follower page.

    Key-values specified to ``options`` is merged to the following base object:

    .. code-block:: python

        {
            '@context': ACTIVITY_STREAMS_CONTEXT,
            'id': id,
            'type': 'OrderedCollectionPage',
            'totalItems': user.follower_count,
            'partOf': user.followers_uri,
            'orderedItems': followers
        }
    """
    page = {
        '@context': ACTIVITY_STREAMS_CONTEXT,
        'id': id,
        'type': 'OrderedCollectionPage',
        'totalItems': user.follower_count,
        'partOf': user.followers_uri,
        'orderedItems': followers,
    }
    if options is not None:
        page.update(options)
    return page


def get_first_follower_page(user: User) -> Dict[str, Any]:
    """Returns the first page of the followers of a given user.
    """
    current_id = f'{user.followers_uri}?page=true'
    followers = list(islice(user.enumerate_followers(PAGE_SIZE), PAGE_SIZE))
    if len(followers) == 0:
        return make_follower_collection_page(user, current_id, [])
    next_key = urlencode(followers[-1])
    return make_follower_collection_page(user, current_id, followers, {
        'next': f'{user.followers_uri}?page=true&after={next_key}',
    })


def get_follower_page_after(user: User, after: str) -> Dict[str, Any]:
    """Returns the followers of a given user after a specified ID.
    """
    after_key = urlencode(after)
    current_id = f'{user.followers_uri}?page=true&after={after_key}'
    followers = list(islice(
        user.enumerate_followers(PAGE_SIZE, after=after),
        PAGE_SIZE,
    ))
    if len(followers) == 0:
        return make_follower_collection_page(user, current_id, [], {
            'prev': f'{user.followers_uri}?page=true&before=~',
        })
    prev_key = urlencode(followers[0])
    next_key = urlencode(followers[-1])
    return make_follower_collection_page(user, current_id, followers, {
        'prev': f'{user.followers_uri}?page=true&before={prev_key}',
        'next': f'{user.followers_uri}?page=true&after={next_key}',
    })


def get_follower_page_before(user: User, before: str) -> Dict[str, Any]:
    """Returns the followers of a given user before a specified ID.
    """
    before_key = urlencode(before)
    current_id = f'{user.followers_uri}?page=true&before={before_key}'
    followers = list(islice(
        user.enumerate_followers(PAGE_SIZE, before=before),
        PAGE_SIZE,
    ))
    if len(followers) == 0:
        return make_follower_collection_page(user, current_id, [], {
            'next': f'{user.followers_uri}?page=true',
        })
    prev_key = urlencode(followers[0])
    next_key = urlencode(followers[-1])
    return make_follower_collection_page(user, current_id, followers, {
        'prev': f'{user.followers_uri}?page=true&before={prev_key}',
        'next': f'{user.followers_uri}?page=true&after={next_key}',
    })


def lambda_handler(event, _context):
    """Runs on AWS Lambda.

    ``event`` must be a ``dict`` similar to the following:

    .. code-block:: python

        {
            'username': '<username>',
            'page': True,
            'after': '<account-id>',
            'before': '<account-id>'
        }

    If ``after`` is specified, followers after ``after`` is returned.

    If ``before`` is specified, followers before ``before`` is returned.
    You can specify tilde ("~") to ``before`` to get the last page.

    You have to specify either of ``after`` and ``before``.

    If ``page`` is ``False`` or omitted, returns a ``dict`` representing a
    collection similar to the following:

    .. code-block:: python

        {
            '@context': 'https://www.w3.org/ns/activitystreams',
            'id': 'https://<domain-name>/users/<username>/followers',
            'type': 'OrderedCollection',
            'totalItems': 123,
            'first': 'https://<domain-name>/users/<username>/followers?page=true'
        }

    If ``page`` is ``True``, returns a ``dict`` representing a collection page
    similar to the following:

    .. code-block:: python

        {
            '@context': 'https://www.w3.org/ns/activitystreams',
            'id': 'https://<domain-name>/users/<username>/followers?page=true',
            'type': 'OrderedCollectionPage',
            'totalItems': 123,
            'next': 'https://<domain-name>/users/<username>/followers?page=true&after=<next-key>',
            'prev': 'https://<domain-name>/users/<username>/followers?page=true&before=<prev-key>',
            'partOf': 'https://<domain-name>/users/<username>/followers'
            'orderedItems': [
                '<follower-id>',
            ]
        }

    ``next`` is omitted if no next follower page exists.
    ``prev`` is omitted if no previous follower page exists.

    :raises KeyError: if ``event`` has no "username".

    :raises BadRequestError: if ``event`` has both of "after" and "before".

    :raises NotFoundError: if the user does not exist.
    """
    LOGGER.debug('obtaining followers: %s', event)
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
    is_page = bool(event.get('page', False))
    if not is_page:
        LOGGER.debug('returning follower collection')
        return {
            '@context': ACTIVITY_STREAMS_CONTEXT,
            'id': user.followers_uri,
            'type': 'OrderedCollection',
            'totalItems': user.follower_count,
            'first': f'{user.followers_uri}?page=true',
        }
    if after is not None:
        LOGGER.debug('obtaining follower after: %s', after)
        return get_follower_page_after(user, after)
    if before is not None:
        LOGGER.debug('obtaining follower before: %s', before)
        return get_follower_page_before(user, before)
    LOGGER.debug('obtaining first follower page')
    return get_first_follower_page(user)
