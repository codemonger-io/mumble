# -*- coding: utf-8 -*-

"""Provides utilities around the objects store.
"""

import logging
import re
from typing import Any, Dict, TypedDict


LOGGER = logging.getLogger('libmumble.objects_store')
LOGGER.setLevel(logging.DEBUG)


class ObjectKey(TypedDict):
    """``dict`` representation of an object key in an S3 bucket.
    """
    bucket: str
    """Name of the S3 bucket."""
    key: str
    """Key of the object."""


def dict_as_object_key(d: Dict[str, Any]) -> ObjectKey: # pylint: disable=invalid-name
    """Casts a given ``dict`` as an ``ObjectKey``.

    :raises TypeError: if ``d`` is incompatible with ``ObjectKey``.
    """
    if not isinstance(d.get('bucket'), str):
        raise TypeError(f'"bucket" must be str but ${type(d.get("bucket"))}')
    if not isinstance(d.get('key'), str):
        raise TypeError(f'"key" must be str but ${type(d.get("key"))}')
    # unfortunately, above checks cannot convince d is ObjectKey
    return d # type: ignore


def get_username_from_key(prefix: str, key: str) -> str:
    """Extracts the username from a given object key.

    :param str prefix: prefix of the key. any characters reserved by regex
    must be properyly escaped.
    """
    pattern = f'^{prefix}\\/users\\/([^/]+)\\/'
    match = re.match(pattern, key)
    if match is None:
        raise ValueError(f'no username in object key: {key}')
    return match.group(1)


def get_username_from_inbox_key(key: str) -> str:
    """Extracts the username from a given object key in the inbox.

    :raises ValueError: if ``key`` is not in the inbox.
    """
    return get_username_from_key('inbox', key)


def get_username_from_staging_outbox_key(key: str) -> str:
    """Extracts the username from a given object key in the staging outbox.

    :raises ValueError: if ``key`` is not in the staging outbox.
    """
    return get_username_from_key('staging', key)
