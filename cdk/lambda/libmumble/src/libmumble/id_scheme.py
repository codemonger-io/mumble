# -*- coding: utf-8 -*-

"""Defines the scheme of IDs.
"""

import logging
import re
from typing import Tuple
from urllib.parse import urlparse
from uuid6 import uuid7


LOGGER = logging.getLogger('libmumble.id_scheme')
LOGGER.setLevel(logging.DEBUG)


def make_user_id(domain_name: str, username: str) -> str:
    """Makes a user ID.

    :param str domain_name: domain name of the Mumble endpoints.
    """
    return f'https://{domain_name}/users/{username}'


def split_user_id(user_id: str) -> Tuple[str, str, str]:
    """Splits a given user ID into the domain name, username, and remaining.

    Examples:

    "https://mumble.codemonger.io/users/kemoto" →
    * "mumble.codemonger.io"
    * "kemoto"
    * ""

    "https://mumble.codemonger.io/users/kemoto/activities/abcdefg"
    * "mumble.codemonger.io"
    * "kemoto"
    * "/activities/abcdefg"

    :returns: tuple of the domain name, username, and remaining.

    :raises ValueError: ``user_id`` is malformed.
    """
    parsed = urlparse(user_id)
    if not parsed.hostname:
        raise ValueError(f'no domain name: {user_id}')
    match = re.match(r'^\/users\/([^/]+)', parsed.path)
    if match is None:
        raise ValueError(f'not a user ID: {user_id}')
    username = match.group(1)
    remaining = parsed.path[len(match.group(0)):]
    return parsed.hostname, username, remaining


def make_user_inbox_uri(user_id: str) -> str:
    """Makes the inbox URI of a given user.
    """
    return f'{user_id}/inbox'


def make_user_outbox_uri(user_id: str) -> str:
    """Makes the outbox URI of a given user.
    """
    return f'{user_id}/outbox'


def make_user_followers_uri(user_id: str) -> str:
    """Makes the URI of the followers list of a given user.
    """
    return f'{user_id}/followers'


def make_user_following_uri(user_id: str) -> str:
    """Makes the URI of the following list of a given user.
    """
    return f'{user_id}/following'


def make_user_key_id(user_id: str) -> str:
    """Makes the key pair ID of a given user.
    """
    return f'{user_id}#main-key'


def generate_user_activity_id(user_id: str) -> str:
    """Generates a random ID for user's activity.
    """
    return f'{user_id}/activities/{generate_unique_part()}'


def parse_user_activity_id(activity_id: str) -> Tuple[str, str, str]:
    """Parses a given activity ID.

    :returns: tuple of the domain name, username, and unique part of the
    activity.

    :raises ValueError: if ``activity_id`` is malformed.
    """
    domain_name, username, remaining = split_user_id(activity_id)
    remaining = remaining.rstrip('/') # allows a trailing slash
    match = re.match(r'\/activities\/([^/]+)$', remaining)
    if match is None:
        raise ValueError(f'invalid activity ID: {activity_id}')
    return domain_name, username, match.group(1)


def generate_user_post_id(user_id: str) -> str:
    """Generates a random ID for user's post.
    """
    return f'{user_id}/posts/{generate_unique_part()}'


def parse_user_post_id(post_id: str) -> Tuple[str, str, str]:
    """Parses a given post ID.

    :returns: tuple of the domain name, username, and unique part of the
    activity.

    :raises ValueError: if ``post_id`` is malformed.
    """
    domain_name, username, remaining = split_user_id(post_id)
    remaining = remaining.rstrip('/') # allows a traling slash
    match = re.match(r'\/posts\/([^/]+)$', remaining)
    if match is None:
        raise ValueError(f'invalid post ID: {post_id}')
    return domain_name, username, match.group(1)


def generate_unique_part() -> str:
    """Generates a unique part of an ID.

    UUID v7 is used to generate a random string.

    :returns: string representation of a generated UUID like
    "00000000-0000-0000-0000-00000000".
    """
    return str(uuid7())
