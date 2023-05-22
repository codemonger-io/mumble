# -*- coding: utf-8 -*-

"""Returns replies to a specific post.

You have to specify the following environment variable:
* ``OBJECT_TABLE_NAME``: name of the DynamoDB table that manages objects.

You may specify the following optional environment variable:
* ``PAGE_SIZE``: maximum number of replies included in a single collection
  page. 12 by default.
"""

from itertools import islice
import logging
import os
from typing import Any, Dict, List, Optional, Tuple
import boto3
from libactivitypub.activity_streams import ACTIVITY_STREAMS_CONTEXT
from libmumble.exceptions import (
    BadConfigurationError,
    BadRequestError,
    NotFoundError,
)
from libmumble.object_table import ObjectTable, PostMetadata, ReplyMetadata
from libmumble.utils import urlencode


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

DEFAULT_PAGE_SIZE = 12
PAGE_SIZE = int(os.environ.get('PAGE_SIZE', DEFAULT_PAGE_SIZE))

OBJECT_TABLE_NAME = os.environ['OBJECT_TABLE_NAME']
OBJECT_TABLE = ObjectTable(boto3.resource('dynamodb').Table(OBJECT_TABLE_NAME))


def get_reply_page(
    post: PostMetadata,
    before: Optional[str]=None,
    after: Optional[str]=None,
) -> Tuple[List[ReplyMetadata], List[str]]:
    """Obtains a collection page of replies to a specified post.

    :raises ValueError: if ``before`` or ``after`` is invalid.

    :raises TooManyAccessError: if access to the DynamoDB table exceeds the
    limit.
    """
    replies = list(islice(
        post.enumerate_replies(PAGE_SIZE, before=before, after=after),
        PAGE_SIZE,
    ))
    return replies, [reply.id for reply in replies]


def make_reply_page(
    post: PostMetadata,
    id: str, # pylint: disable=invalid-name, redefined-builtin
    replies: List[str],
    options: Optional[Dict[str, Any]]=None,
) -> Dict[str, Any]:
    """Makes a ``dict`` object of a collection page of replies.
    """
    if options is None:
        options = {}
    return {
        '@context': ACTIVITY_STREAMS_CONTEXT,
        'id': id,
        'type': 'OrderedCollectionPage',
        'partOf': post.replies_id,
        'totalItems': post.reply_count,
        'orderedItems': replies,
        **options,
    }


def get_first_reply_page(post: PostMetadata) -> Dict[str, Any]:
    """Obtains the first collection page of replies to a sepcified post.

    :raises TooManyAccessError: if access to the DynamoDB table exceeds the
    limit.
    """
    current_id = f'{post.replies_id}?page=true'
    meta_replies, replies = get_reply_page(post)
    if len(meta_replies) == 0:
        return make_reply_page(post, current_id, [])
    next_key = urlencode(meta_replies[-1].serialized_key)
    return make_reply_page(post, current_id, replies, {
        'next': f'{post.replies_id}?page=true&before={next_key}',
    })


def get_reply_page_before(post: PostMetadata, before: str) -> Dict[str, Any]:
    """Obtains the collection page of replies to a specified post before a
    given ID.

    :raises TooManyAccessError: if access to the DynamoDB table exceeds the
    limit.
    """
    current_id = f'{post.replies_id}?page=true&before={urlencode(before)}'
    meta_replies, replies = get_reply_page(post, before=before)
    if len(meta_replies) == 0:
        oldest_key = urlencode(ReplyMetadata.OLDEST_SERIALIZED_KEY)
        return make_reply_page(post, current_id, [], {
            'prev': f'{post.replies_id}?page=true&after={oldest_key}'
        })
    prev_key = urlencode(meta_replies[0].serialized_key)
    next_key = urlencode(meta_replies[-1].serialized_key)
    return make_reply_page(post, current_id, replies, {
        'prev': f'{post.replies_id}?page=true&after={prev_key}',
        'next': f'{post.replies_id}?page=true&before={next_key}',
    })


def get_reply_page_after(post: PostMetadata, after: str) -> Dict[str, Any]:
    """Obtains the collection page of replies ot a specified post after a
    given ID.

    :raises TooManyAccessError: if access to the DynamoDB table exceeds the
    limit.
    """
    current_id = f'{post.replies_id}?page=true&after={urlencode(after)}'
    meta_replies, replies = get_reply_page(post, after=after)
    if len(meta_replies) == 0:
        return make_reply_page(post, current_id, [], {
            'next': f'{post.replies_id}?page=true',
        })

    prev_key = urlencode(meta_replies[0].serialized_key)
    next_key = urlencode(meta_replies[-1].serialized_key)
    return make_reply_page(post, current_id, replies, {
        'prev': f'{post.replies_id}?page=true&after={prev_key}',
        'next': f'{post.replies_id}?page=true&before={next_key}',
    })


def lambda_handler(event, _context):
    """Runs on AWS Lambda.

    ``event`` must be a ``dict`` similar to the following:

    .. code-block:: python

        {
            'username': '<username>',
            'uniquePart': '<unique-part>',
            'page': True,
            'after': '<after-id>',
            'before': '<before-id>'
        }

    If ``page`` is ``False`` or omitted, returns a collection object similar
    to the following:

    .. code-block:: python

        {
            '@context': 'https://www.w3.org/ns/activitystreams',
            '@id': 'https://<domain-name>/users/<username>/posts/<unique-part>/replies',
            'type': 'OrderedCollection',
            'totalItems': 123,
            'first': 'https://<domain-name>/users/<username>/posts/<unique-part>/replies?page=true'
        }

    If ``page`` is ``True``, returns a collection page object similar to the
    following:

    .. code-block:: python

        {
            '@context': 'https://www.w3.org/ns/activitystreams',
            '@id': 'https://<domain-name>/users/<username>/posts/<unique-part>/replies?page=true',
            'type': 'OrderedCollectionPage',
            'partOf': 'https://<domain-name>/users/<username>/posts/<unique-part>/replies',
            'totalItems': 123,
            'next': 'https://<domain-name>/users/<username>/posts/<unique-part>/replies?page=true&before=<before-id>',
            'prev': 'https://<domain-name>/users/<username>/posts/<unique-part>/replies?page=true&after=<after-id>'
        }

    :raises BadConfigurationError: if ``event`` lacks any mandatory property,
    or if both of ``before`` and ``after`` are specified.

    :raises BadRequestError: if ``before`` or ``after`` is invalid.

    :raises NotFoundError: if the specified post does not exist,
    or if the specified post is not public.

    :raises TooManyAccessError: if access to the DynamoDB table exceeds the
    limit.
    """
    LOGGER.debug('obtaining replies: %s', event)
    try:
        username = event['username']
        unique_part = event['uniquePart']
    except KeyError as exc:
        raise BadConfigurationError(f'{exc}') from exc
    page = bool(event.get('page', False))
    after = event.get('after')
    before = event.get('before')
    post = OBJECT_TABLE.find_user_post(username, unique_part)
    if post is None or not post.is_public:
        raise NotFoundError(
            f'no such post: username={username}, unique part={unique_part}',
        )
    if not page:
        return {
            **post.make_reply_collection(),
            '@context': ACTIVITY_STREAMS_CONTEXT,
        }
    try:
        if before is not None:
            return get_reply_page_before(post, before)
        if after is not None:
            return get_reply_page_after(post, after)
        return get_first_reply_page(post)
    except ValueError as exc:
        raise BadRequestError(f'{exc}') from exc
