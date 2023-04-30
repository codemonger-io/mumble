# -*- coding: utf-8 -*-

"""Stages a response activity.

You have to specify the following environment variable:
* ``USER_TABLE_NAME``: name of the DynamoDB table that stores user information.
"""

import json
import logging
import os
from typing import Any, Dict
import boto3
from libactivitypub.activity import Activity
from libactivitypub.activity_streams import (
    ACTIVITY_STREAMS_CONTEXT,
    post as activity_streams_post,
)
from libactivitypub.actor import Actor
from libactivitypub.objects import generate_id
from libmumble.exceptions import (
    BadConfigurationError,
    CommunicationError,
    CorruptedDataError,
    NotFoundError,
    TransientError,
)
from libmumble.user_table import UserTable, parse_user_id
import requests


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
# turns on logs from some dependencies
logging.getLogger('libactivitypub').setLevel(logging.DEBUG)
logging.getLogger('libmumble').setLevel(logging.DEBUG)

USER_TABLE_NAME = os.environ['USER_TABLE_NAME']
USER_TABLE = UserTable(boto3.resource('dynamodb').Table(USER_TABLE_NAME))


def get_private_key(key_path: str) -> str:
    """Obtains the private key at a given path in the Parameter Store on AWS
    Systems Manager.

    :raises BadConfigurationError: if no private key is found.
    """
    ssm = boto3.client('ssm')
    try:
        res = ssm.get_parameter(Name=key_path, WithDecryption=True)
    except (
        ssm.exceptions.InvalidKeyId,
        ssm.exceptions.ParameterNotFound,
    ) as exc:
        raise BadConfigurationError(f'no private key: {key_path}') from exc
    return res['Parameter']['Value']


def complete_object(obj: Dict[str, Any], username: str, domain_name: str):
    """Completes a given object as an ActivityStream object.

    Assigns an object ID.
    Adds the JSON-LD context field.

    Modifies ``obj``.

    :returns: ``obj`` itself.
    """
    unique_part = generate_id()
    obj['id'] = f'https://{domain_name}/users/{username}/objects/{unique_part}'
    obj['@context'] = ACTIVITY_STREAMS_CONTEXT


def lambda_handler(event, _context):
    """Runs on AWS Lambda.

    ``event`` must be a ``dict`` similar to the following:

    .. code-block:: python

        {
            'type': '<activity-type>',
            'actor': '<actor-id>',
            'object': {
                ...
            }
        }

    :raises CorruptedDataError: if ``actor`` is not ``str``, if ``actor`` does
    not represent the user in this service.

    :raises NotFoundError: if the actor (user) does not exist.

    :raises BadConfigurationError: if user's private key is not found.

    :raises TooManyAccessError: if there are too many access to the user table.

    :raises TransientError: if a request to the other server times out,
    or returns 429 status code.

    :raises CommunicationError: if the other server returns a non-transient
    error.
    """
    LOGGER.debug('staging response: %s', event)
    actor_id = event.get('actor')
    if not isinstance(actor_id, str):
        raise CorruptedDataError(f'actor must be str but: {type(actor_id)}')
    try:
        domain_name, username = parse_user_id(actor_id)
    except ValueError as exc:
        raise CorruptedDataError(f'{exc}') from exc
    LOGGER.debug('looking up user: %s@%s', username, domain_name)
    user = USER_TABLE.find_user_by_username(username, domain_name)
    if user is None:
        raise NotFoundError(f'no such user: {username}')
    LOGGER.debug('obtaining private key')
    private_key_pem = get_private_key(user.private_key_path)
    LOGGER.debug('parsing object')
    obj = event.get('object')
    if not isinstance(obj, dict):
        raise CorruptedDataError(f'object must be dict but {type(obj)}')
    try:
        activity = Activity.parse_object(obj)
    except (TypeError, ValueError) as exc:
        raise CorruptedDataError(f'{exc}') from exc
    LOGGER.debug('resolving recipient: %s', activity.actor_id)
    try:
        recipient = Actor.resolve_uri(activity.actor_id)
    except requests.Timeout as exc:
        raise TransientError(f'request timed out: {exc}') from exc
    except requests.HTTPError as exc:
        LOGGER.error('http request failed: %s', exc)
        if exc.response.status_code == 429:
            raise TransientError(f'too many requests: {exc}') from exc
        raise CommunicationError(f'{exc}') from exc
    LOGGER.debug('posting to inbox: %s', recipient.inbox.uri)
    complete_object(event, username, domain_name)
    try:
        res = activity_streams_post(
            recipient.inbox.uri,
            body=json.dumps(event).encode('utf-8'),
            private_key={
                'key_id': f'https://{domain_name}/users/{username}#main-key',
                'private_key_pem': private_key_pem,
            },
        )
    except requests.Timeout as exc:
        raise TransientError(f'request timed out: {exc}') from exc
    except requests.HTTPError as exc:
        LOGGER.error('http request failed: %s', exc)
        if exc.response.status_code == 429:
            raise TransientError(f'too many requests: {exc}') from exc
        raise CommunicationError(f'{exc}') from exc
    LOGGER.debug('inbox responded with: %s', res.text)
