# -*- coding: utf-8 -*-

"""Receives an activity posted to the inbox of a given user.

You have to specify the following environment variables:
* ``USER_TABLE_NAME``: name of the DynamoDB table that stores user information.
* ``OBJECTS_BUCKET_NAME``: name of the S3 bucket that stores received objects.
* ``DOMAIN_NAME_PARAMETER_PATH``: path to the parameter that stores the domain
  name in Parameter Store on AWS Systems Manager.
"""

import json
import logging
import os
import boto3
from libactivitypub.activity import Activity
from libactivitypub.actor import Actor
from libactivitypub.signature import (
    VerificationError,
    parse_signature,
    verify_signature_and_headers,
)
from libmumble.exceptions import (
    BadRequestError,
    NotFoundError,
    UnauthorizedError,
)
from libmumble.parameters import get_domain_name
from libmumble.user_table import UserTable
from libmumble.utils import to_urlsafe_base64
import requests


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
# turns on logs from some dependencies
logging.getLogger('libactivitypub').setLevel(logging.DEBUG)
logging.getLogger('libmumble').setLevel(logging.DEBUG)

DOMAIN_NAME = get_domain_name(boto3.client('ssm'))

# user table
USER_TABLE_NAME = os.environ['USER_TABLE_NAME']
USER_TABLE = UserTable(boto3.resource('dynamodb').Table(USER_TABLE_NAME))

# bucket for objects
OBJECTS_BUCKET_NAME = os.environ['OBJECTS_BUCKET_NAME']


def save_activity_in_inbox(activity_data: str, digest: str, recipient: str):
    """Saves a given activity in the inbox of a specified user.

    :param str activity_data: string representation of the activity object
    to be saved.

    :param str digest: SHA-256 hash of ``activity_data``. in the form of
    "SHA-256=<SHA256 hash>".

    :param str recipient: recipient of the activity.

    :raises ValueError: if ``digest`` does not start with "SHA-256=".
    """
    digest_prefix = 'SHA-256='
    if not digest.startswith(digest_prefix):
        raise ValueError(f'digest must start with "{digest_prefix}"')
    digest = digest[len(digest_prefix):]
    s3_client = boto3.client('s3')
    object_key = f'inbox/users/{recipient}/{to_urlsafe_base64(digest)}.json'
    LOGGER.debug('saving activity: %s', object_key)
    res = s3_client.put_object(
        Bucket=OBJECTS_BUCKET_NAME,
        Key=object_key,
        Body=activity_data.encode('utf-8'),
        ChecksumSHA256=digest,
    )
    # TODO: what kind of errors should we handle?
    LOGGER.debug('saved activity: %s', res)


def lambda_handler(event, _context):
    """Runs on AWS Lambda.

    ``event`` must be a ``dict`` similar to the following:

    .. code-block:: python

        {
            'username': '<username>',
            'signature': '<signature>',
            'date': '<date>',
            'digest': '<digest>',
            'contentType': '<content-type>',
            'body': '<body>'
        }

    ``signature`` is the Signature header value.

    ``date`` is the Date header value.

    ``digest`` is the Digest header value.

    ``contentType`` is the Content-Type header value.

    ``body`` is the request body as a raw string.
    The raw body is necessary to verify the signature.

    :raises UnauthorizedError: if the signature is invalid.

    :raises BadRequestError: if the activity is unsupported.

    :raises NotFoundError: if no user is associated with ``username``.

    :raises TooManyAccessError: if there are too many requests.
    """
    username = event['username']
    LOGGER.debug('processing activity sent to: %s', username)

    LOGGER.debug('parsing signature')
    try:
        signature = parse_signature(event['signature'])
    except ValueError as exc:
        raise UnauthorizedError(f'bad signature: {exc}') from exc

    LOGGER.debug('resolving signer: %s', signature['key_id'])
    try:
        signer = Actor.resolve_uri(signature['key_id'])
    except requests.HTTPError as exc:
        raise UnauthorizedError(
            f'failed to resolve signer: {signature["key_id"]}',
        ) from exc
    except ValueError as exc:
        raise UnauthorizedError(f'invalid actor: {exc}') from exc

    LOGGER.debug('loading public key')
    try:
        public_key = signer.public_key
    except (AttributeError, TypeError) as exc:
        raise UnauthorizedError(f'invalid actor: {exc}') from exc
    if public_key['id'] != signature['key_id']:
        raise UnauthorizedError(f'key ID mismatch: {signature["key_id"]}')

    LOGGER.debug('verifying signature')
    body = event['body']
    try:
        verify_signature_and_headers(
            signature,
            public_key['publicKeyPem'],
            header_values={
                '(request-target)': f'post /users/{username}/inbox',
                'body': body,
                'host': DOMAIN_NAME,
                'date': event['date'],
                'digest': event['digest'],
                'content-type': event['contentType'],
            },
        )
    except (KeyError, ValueError, VerificationError) as exc:
        raise UnauthorizedError(f'failed to authenticate: {exc}') from exc

    # once the signature is verified, we can parse the body
    LOGGER.debug('parsing activity')
    try:
        activity = Activity.parse_object(json.loads(body))
    except ValueError as exc:
        raise BadRequestError(f'{exc}') from exc
    if signer.id != activity.actor_id:
        raise UnauthorizedError(
            f'signer and actor mismatch: {signer.id} != {activity.actor_id}',
        )

    LOGGER.debug('looking up user: %s', username)
    user = USER_TABLE.find_user_by_username(username, DOMAIN_NAME)
    if user is None:
        raise NotFoundError(f'no such user: {username}')

    # saves the activity in an S3 bucket
    try:
        save_activity_in_inbox(body, event['digest'], username)
    except ValueError as exc:
        raise BadRequestError(f'{exc}') from exc
