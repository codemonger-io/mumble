# -*- coding: utf-8 -*-

"""Delivers an activity to a single recipient.

You have to specify the following environment variable:
* ``OBJECTS_BUCKET_NAME``: name of the S3 bucket that stores objects.
* ``USER_TABLE_NAME``: name of the DynamoDB table that stores user information.
* ``DOMAIN_NAME_PARAMETER_PATH``: path to the parameter containing the domain
  name in Parameter Store on AWS Systems Manager.
"""

import json
import logging
import os
import re
from urllib.parse import urlparse
import boto3
from libactivitypub.activity import Activity
from libactivitypub.activity_streams import post as activity_streams_post
from libmumble.exceptions import (
    BadConfigurationError,
    CorruptedDataError,
    NotFoundError,
    TransientError,
)
from libmumble.objects_store import save_object
from libmumble.parameters import get_domain_name
from libmumble.user_table import UserTable, parse_user_id
import requests


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

OBJECTS_BUCKET_NAME = os.environ['OBJECTS_BUCKET_NAME']

USER_TABLE_NAME = os.environ['USER_TABLE_NAME']
USER_TABLE = UserTable(boto3.resource('dynamodb').Table(USER_TABLE_NAME))

# caching the domain name should not harm
DOMAIN_NAME = get_domain_name(boto3.client('ssm'))


def get_object_id_from_activity_id(activity_id: str) -> str:
    """Extracts object ID (unique part) from a given activity ID.

    :raises ValueError: if ``activity_id`` is malformed.
    """
    parsed_uri = urlparse(activity_id)
    match = re.match(r'^\/users\/[^/]+\/activities\/([^/]+)', parsed_uri.path)
    if match is None:
        raise ValueError(f'malformed activity ID: {activity_id}')
    return match.group(1)


def lambda_handler(event, _context):
    """Runs on AWS Lambda.

    ``event`` must be a ``dict`` similar to the following:

    .. code-block:: python

        {
            'activity': {
                '@context': 'https://www.w3.org/ns/activitystreams',
                'id': '<activity-id>',
                'type': '<activity-type>'
            },
            'recipient': '<inbox-uri>'
        }

    :raises BadConfigurationError: if the actor does not belong to the domain
    of this service.

    :raises NotFoundError: if the actor (user) does not exist.

    :raises CorruptedDataError: if the activity does not have "@context",
    "id", or "type".

    :raises TransientError: if an http request times out,
    or returns 429 status code.

    :raises ValueError: if data is invalid.

    :raises TypeError: if data has a type error.
    """
    LOGGER.debug('delivering activity: %s', event)
    activity = Activity.parse_object(event['activity'])
    if not activity.is_deliverable():
        raise CorruptedDataError('activity is not ready to be delivered')
    recipient = event['recipient']
    domain_name, username = parse_user_id(activity.actor_id)
    if domain_name != DOMAIN_NAME:
        raise BadConfigurationError(
            f'actor domain mismatch: {domain_name} != {DOMAIN_NAME}',
        )
    object_id = get_object_id_from_activity_id(activity.id)
    LOGGER.debug('looking up user: %s@%s', username, domain_name)
    user = USER_TABLE.find_user_by_username(username, domain_name)
    if user is None:
        raise NotFoundError(f'no such user: {username}')
    LOGGER.debug('saving activity in outbox')
    save_object(
        boto3.client('s3'),
        {
            'bucket': OBJECTS_BUCKET_NAME,
            'key': f'outbox/users/{username}/{object_id}.json',
        },
        activity,
    )
    try:
        res = activity_streams_post(
            recipient,
            body=json.dumps(activity.to_dict()).encode('utf-8'),
            private_key={
                'key_id': user.key_id,
                'private_key_pem': user.get_private_key(boto3.client('ssm')),
            },
        )
        LOGGER.debug('recipient responded with: %s', res.text)
    except requests.Timeout as exc:
        raise TransientError(f'http request timed out: {exc}') from exc
    except requests.HTTPError as exc:
        LOGGER.error('http request failed: %s', exc)
        if exc.response.status_code == 429:
            raise TransientError(f'too many http requests: {exc}') from exc
        raise
