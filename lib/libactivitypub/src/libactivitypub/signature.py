# -*- coding: utf-8 -*-

"""Parsing and verification of a signature.

A signature used by Mastodon, which has the form
``keyId="..."[,algorithm="..."],headers="(request-target) host date[ digest]",signature="..."``

References:
* https://docs.joinmastodon.org/spec/security/
"""

import base64
from datetime import datetime
from email.utils import parsedate_to_datetime
import hashlib
import logging
import math
import re
from typing import Dict, Iterable, List, Tuple, TypedDict
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
import pytz


LOGGER = logging.getLogger('libactivitypub.signature')
LOGGER.setLevel(logging.DEBUG)

DEFAULT_SIGNING_ALGORITHM = 'rsa-sha256'
"""Default algorithm for signing, formally called RSASSA-PKCS1-v1_5."""

SIGNATURE_WINDOW_IN_SECONDS = 30
"""Allowed gap between the signature timestamp and the current time."""

MANDATORY_HEADERS = [
    '(request-target)',
    'host',
    'date',
]
"""Mandatory headers to be signed."""


class VerificationError(Exception):
    """Raised if signature verification fails.
    """


class Signature(TypedDict):
    """Signature.
    """
    key_id: str
    """Requestor's ID."""
    algorithm: str
    """Digest algorithm."""
    headers: str
    """Headers involved in signing."""
    signature: str
    """Base64-encoded signature string."""


def parse_signature(signature: str) -> Signature:
    """Parses a given signture header value.

    A signature used by Mastodon, which has the form
    ``keyId="..."[,algorithm="..."],headers="(request-target) host date[ digest]",signature="..."``

    If ``algorithm`` is omitted, "rsa-sha256" by default.

    :raises ValueError: if the format of ``signature`` is wrong.
    Parameters cannot be empty.
    """
    pattern = (
        r'^keyId="(.*?)"\s*'
            # non-greedy, otherwise, eats "algorithm"
            # empty "keyId" is accepted, but rejected afterward.
            # to prevent "keyId" from swallowing empty "algorithm".
        r'(?:,\s*algorithm="(.*)"\s*)?'
            # empty "algorithm" is accepted, but rejected afterward.
            # to prevent "keyId" from swallowing empty "algorithm".
        r',\s*headers="(.+)"\s*'
        r',\s*signature="(.+)"\s*$'
    )
    match = re.match(pattern, signature)
    if match is None:
        raise ValueError('bad signature format')
    key_id = match.group(1)
    if not key_id:
        raise ValueError('keyId must not be empty')
    algorithm = match.group(2)
    if not algorithm:
        if algorithm is not None:
            raise ValueError(
                'algorithm may be omitted but cannot be set to empty',
            )
        algorithm = DEFAULT_SIGNING_ALGORITHM
    return {
        'key_id': key_id,
        'algorithm': algorithm,
        'headers': match.group(3),
        'signature': match.group(4),
    }


def parse_signature_headers_parameter(headers: str) -> List[str]:
    """Parses a given headers parameter in a signature.

    Example: "(request-target) host date digest content-type"

    The following headers are mandatory:
    * ``(request-target)``
    * ``host``
    * ``date``

    :raises ValueError: if any of the mandatory headers is missing in
    ``headers``, or if more than one whitespace characters are used as
    a delimiter.
    """
    i_headers = headers.split(' ')
    if any((header not in i_headers for header in MANDATORY_HEADERS)):
        raise ValueError(
            f'mandatory header {MANDATORY_HEADERS} is missing in {headers}',
        )
    if any((not header for header in i_headers)):
        raise ValueError(f'malformed headers: {headers}')
    return i_headers


def is_valid_signature_date(date: str) -> bool:
    """Returns if a given date in a signature is valid.

    ``date`` is valid if it is within the current time ± 30 seconds.

    :returns: whether ``date`` is valid.

    :raise TypeError: if ``date`` is malformed.
    """
    timestamp = parsedate_to_datetime(date)
    elapsed = datetime.now(tz=pytz.utc) - timestamp
    LOGGER.debug('elapsed seconds: %.2f', elapsed.total_seconds())
    return math.fabs(elapsed.total_seconds()) <= SIGNATURE_WINDOW_IN_SECONDS


def digest_request_body(body: bytes) -> str:
    """Calculates the SHA-256 digest of a given request body.

    :returns: SHA-256 digest in the form "SHA-256=<Base64 hash>".
    """
    hasher = hashlib.sha256()
    hasher.update(body)
    return f'SHA-256={base64.b64encode(hasher.digest()).decode()}'


def is_valid_request_body(body: str, digest: str) -> bool:
    """Returns if a given request body and digest match.

    ``digest`` must be in the form "SHA-256=<SHA-256 hash>".

    :returns: whether the SHA-256 hash of ``body`` matches ``digest``.
    """
    return digest_request_body(body.encode('utf-8')) == digest


def concatenate_headers(
    headers: Iterable[str],
    header_values: Dict[str, str],
) -> str:
    """Concatenate given headers.

    The result is to be used to verify or sign.
    """
    lines = [f'{header}: {header_values[header]}' for header in headers]
    return '\n'.join(lines)


def verify_headers(
    headers: Iterable[str],
    header_values: Dict[str, str],
    signature: str,
    public_key_pem: str,
):
    """Verifies given headers.

    A message to be verified is built in the following steps:
    1. take values associated with each item in ``headers``
    2. concatenate taken values with '\n'

    The signing algorithm is ``RSASSA-PKCS1-v1_5``.

    :raises VerificationError: if the signature cannot be verified.
    """
    message = concatenate_headers(headers, header_values)
    LOGGER.debug('message to verify: %s', message)
    signature_bytes = base64.b64decode(signature)
    try:
        rsa_key = RSA.import_key(public_key_pem)
    except (IndexError, TypeError, ValueError) as exc:
        raise VerificationError(f'invalid public key: {exc}') from exc
    hashed = SHA256.new(message.encode('utf-8'))
    verifier = pkcs1_15.new(rsa_key)
    try:
        verifier.verify(hashed, signature_bytes)
    except (TypeError, ValueError) as exc:
        raise VerificationError(f'signature is not authentic: {exc}') from exc


def sign_headers(
    headers: Iterable[str],
    header_values: Dict[str, str],
    private_key_pem: str,
) -> str:
    """Signs given headers.

    :returns: Base64-encoded signature.

    :raises ValueError: if the private key is invalid.
    """
    message = concatenate_headers(headers, header_values)
    LOGGER.debug('message to be signed: %s', message)
    try:
        key = RSA.import_key(private_key_pem)
    except (IndexError, TypeError, ValueError) as exc:
        raise ValueError(f'invalid private key: {exc}') from exc
    message_hash = SHA256.new(message.encode('utf-8'))
    try:
        signature_bytes = pkcs1_15.new(key).sign(message_hash)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'failed to sign: {exc}') from exc
    return base64.b64encode(signature_bytes).decode('utf-8')


def verify_signature_and_headers(
    signature: Signature,
    public_key_pem: str,
    header_values: Dict[str, str],
):
    """Verifies a given signature and headers.

    ``header_values`` must be a ``dict`` similar to the following (other keys
    may be included but ignored):

    .. code-block:: python

        {
            '(request-target)': '<request-target>',
            'body': '<request-body>',
            'host': '<host>',
            'date': '<date>',
            'digest': '<body-digest>',
            'content-type': '<content-type>'
        }

    ``header_values`` may omit keys not included in ``signature['headers']``.

    This function checks if:
    * the signing altorithm is supported
    * the date is within a window
    * the headers is valid
    * the calculated digest of the body matches the given digest
    * the header values are authentic

    :raises VerificationError: if ``header_values`` is not authentic,
    or if the calculated digest of the body does not match the given digest.

    :raises KeyError: if ``header_values`` does not have required keys.

    :raises ValueError: if ``signature['headers']`` is invalid,
    or if the algorithm is other than "rsa-sha256",
    or if the date is out of the window.
    """
    # only the default algorithm is supported
    algorithm = signature['algorithm']
    LOGGER.debug('cheking algorithm: %s', algorithm)
    if algorithm != DEFAULT_SIGNING_ALGORITHM:
        raise ValueError(f'unsupported signing algorithm: {algorithm}')
    # validates the date
    date = header_values['date']
    LOGGER.debug('validating date: %s', date)
    if not is_valid_signature_date(date):
        raise ValueError(f'date is out of bounds: {date}')
    # parses the headers
    LOGGER.debug('parsing headers: %s', signature['headers'])
    headers = parse_signature_headers_parameter(signature['headers'])
    # validates the body if a digest is given
    if 'digest' in headers:
        LOGGER.debug('validating body')
        if not is_valid_request_body(
            header_values['body'],
            header_values['digest'],
        ):
            raise VerificationError('request body digest mismatch')
    # verifies the headers
    LOGGER.debug('verifying headers')
    verify_headers(
        headers,
        header_values,
        signature['signature'],
        public_key_pem,
    )


def make_signature_header(
    key_id: str,
    private_key_pem: str,
    header_values: Iterable[Tuple[str, str]],
) -> str:
    """Makes a signature header value.

    The header values in the message to be signed is ordered in the same order
    in ``header_values``.

    :params Iterable[Tuple[str, str]] header_values: each item must be a pair
    of a header name and the value.

    :raises ValueError: if the private key is invalid.
    """
    headers = [header for header, _ in header_values]
    signature = sign_headers(headers, dict(header_values), private_key_pem)
    return (
        f'keyId="{key_id}",'
        'algorithm="rsa-sha256",'
        f'headers="{" ".join(headers)}",'
        f'signature="{signature}"'
    )
