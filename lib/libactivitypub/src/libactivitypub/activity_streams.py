# -*- coding: utf-8 -*-

"""Provides utilities to communicate with endpoints responding with
ActivityStreams.
"""

from email.utils import formatdate
import logging
from typing import Any, Dict, TypedDict
from urllib.parse import urlparse
import requests
from . import VERSION
from .mime_types import ACTIVITY_STREAMS_MIME_TYPES
from .signature import digest_request_body, make_signature_header


LOGGER = logging.getLogger('libactivitypub.activity_streams')
LOGGER.setLevel(logging.DEBUG)

ACTIVITY_STREAMS_CONTEXT = 'https://www.w3.org/ns/activitystreams'
"""JSON-LD context for ActivityStream."""

ACTIVITY_STREAMS_PUBLIC_ADDRESS = 'https://www.w3.org/ns/activitystreams#Public'
"""Public address for public posts."""

MUMBLE_USER_AGENT = f'Mumble/{VERSION}'

DEFAULT_REQUEST_TIMEOUT = 30.0
"""Default timeout of requests."""


class PrivateKey(TypedDict):
    """Private key.
    """
    key_id: str
    """Key ID associated with the private key."""
    private_key_pem: str
    """PEM representation of the private key."""


def get(endpoint: str) -> Dict[str, Any]:
    """Makes a GET request to a given endpoint.

    :raises requests.HTTPError: if the HTTP request fails.

    :raises requests.Timeout: if the request times out.
    """
    res = requests.get(
        endpoint,
        headers={
            'User-Agent': MUMBLE_USER_AGENT,
            'Accept': ', '.join(ACTIVITY_STREAMS_MIME_TYPES),
        },
        timeout=DEFAULT_REQUEST_TIMEOUT,
    )
    res.raise_for_status()
    return res.json()


def post(
    endpoint: str,
    body: bytes,
    private_key: PrivateKey,
) -> requests.Response:
    """Makes a POST request to a given endpoint.

    The request is signed with ``private_key``.

    The signature header will include the following header values:
    * (request-target): extracted from ``endpoint``
    * host: extracted from ``endpoint``
    * date: use current datetime
    * digest: calculated from ``body``
    * content-type: "application/json"

    :raises ValueError: if ``endpoint`` contains no host,
    or if the private key is invalid.

    :raises requests.HTTPError: if the HTTP request fails.

    :raises requests.Timeout: if the request times out.
    """
    parsed_uri = urlparse(endpoint)
    path = parsed_uri.path
    host = parsed_uri.hostname
    if not host:
        raise ValueError(f'no host in endpoint: {endpoint}')
    date = formatdate(usegmt=True)
    body_digest = digest_request_body(body)
    signature_header = make_signature_header(
        private_key['key_id'],
        private_key['private_key_pem'],
        [
            ('(request-target)', f'post {path}'),
            ('host', host),
            ('date', date),
            ('digest', body_digest),
            ('content-type', 'application/json'),
        ],
    )
    LOGGER.debug('signature header: %s', signature_header)
    res = requests.post(
        endpoint,
        data=body,
        headers={
            'User-Agent': MUMBLE_USER_AGENT,
            'Accept': ', '.join(ACTIVITY_STREAMS_MIME_TYPES),
            'Content-Type': 'application/json',
            'Date': date,
            'Digest': body_digest,
            'Signature': signature_header,
        },
        timeout=DEFAULT_REQUEST_TIMEOUT,
    )
    res.raise_for_status()
    return res
