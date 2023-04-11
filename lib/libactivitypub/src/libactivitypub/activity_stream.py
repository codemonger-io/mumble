# -*- coding: utf-8 -*-

"""Provides utilities to communicate with endpoints responding with
ActivityStream.
"""

import logging
from typing import Any, Dict
import requests
from .mime_types import DEFAULT_ACTIVITY_STREAM_MIME_TYPE


LOGGER = logging.getLogger('libactivitypub.activity_stream')
LOGGER.setLevel(logging.DEBUG)


DEFAULT_REQUEST_TIMEOUT = 30.0
"""Default timeout of requests."""


def get(endpoint: str) -> Dict[str, Any]:
    """Makes a GET request to a given endpoint.

    :raises requests.HTTPError: if an HTTP request fails.
    """
    res = requests.get(
        endpoint,
        headers={
            'Accept': DEFAULT_ACTIVITY_STREAM_MIME_TYPE,
        },
        timeout=DEFAULT_REQUEST_TIMEOUT,
    )
    res.raise_for_status()
    return res.json()
