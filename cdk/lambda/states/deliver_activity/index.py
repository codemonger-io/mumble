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
from libactivitypub.activity_streams import post as activity_streams_post
from libmumble.exceptions import (
    BadConfigurationError,
    CorruptedDataError,
    NotFoundError,
    TransientError,
)
from libmumble.objects_store import dict_as_object_key, load_activity
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


def lambda_handler(event, _context):
    """Runs on AWS Lambda.

    ``event`` must be a ``dict`` similar to the following:

    .. code-block:: python

        {
            'activity': {
                'bucket': '<bucket-name>',
                'key': '<object-key>'
            },
            'recipient': '<inbox-uri>'
        }

    :raises BadConfigurationError: if a wrong objects bucket is given,
    or if the actor does not belong to the domain of this service.

    :raises CorruptedDataError: if the activity does not have "@context",
    "id", or "type".

    :raises NotFoundError: if the actor (user) does not exist.

    :raises TransientError: if an HTTP request fails with a transient error;
    e.g., timeout, 429 status code.

    :raises requests.HTTPError: if an HTTP request fails with a non-transient
    error.

    :raises ValueError: if data is invalid.

    :raises TypeError: if data has a type error.
    """
    LOGGER.debug('delivering activity: %s', event)
    object_key = dict_as_object_key(event['activity'])
    if object_key['bucket'] != OBJECTS_BUCKET_NAME:
        raise BadConfigurationError(
            'objects bucket mismatch:'
            f' {OBJECTS_BUCKET_NAME} != {object_key["bucket"]}',
        )
    LOGGER.debug('loading activity: %s', object_key)
    activity = load_activity(boto3.client('s3'), object_key)
    if not activity.is_deliverable():
        raise CorruptedDataError('activity is not ready to be delivered')
    recipient = event['recipient']
    domain_name, username = parse_user_id(activity.actor_id)
    if domain_name != DOMAIN_NAME:
        raise BadConfigurationError(
            f'actor domain mismatch: {domain_name} != {DOMAIN_NAME}',
        )
    LOGGER.debug('looking up user: %s@%s', username, domain_name)
    user = USER_TABLE.find_user_by_username(username, domain_name)
    if user is None:
        raise NotFoundError(f'no such user: {username}')
    try:
        LOGGER.debug('sending activity')
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
