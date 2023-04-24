# -*- coding: utf-8 -*-

"""Provides utilities around the objects store.
"""

import logging
import re


LOGGER = logging.getLogger('libmumble.objects_store')
LOGGER.setLevel(logging.DEBUG)


def get_username_from_inbox_key(key: str) -> str:
    """Extracts the username from a given object key in the inbox.

    :raises ValueError: if ``key`` is not in the inbox.
    """
    pattern = r'^inbox\/users\/([^/]+)\/'
    match = re.match(pattern, key)
    if match is None:
        raise ValueError(f'no username in object key: {key}')
    return match.group(1)
