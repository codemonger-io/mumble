# -*- coding: utf-8 -*-

"""Receives an outbound activity or object from a user and saves it in the
staging outbox of the user.

You have specify the following environment variables:
* ``USER_TABLE_NAME``: name of the DynamoDB table that manages user information.
* ``OBJECTS_BUCKET_NAME``: name of the S3 bucket that manages objects.
"""

import logging
import os
import boto3
from libactivitypub.objects import DictObject
from libmumble.exceptions import BadRequestError, ForbiddenError, NotFoundError
from libmumble.objects_store import save_object
from libmumble.user_table import UserTable


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

OBJECTS_BUCKET_NAME = os.environ['OBJECTS_BUCKET_NAME']

USER_TABLE_NAME = os.environ['USER_TABLE_NAME']
USER_TABLE = UserTable(boto3.resource('dynamodb').Table(USER_TABLE_NAME))


def lambda_handler(event, _context):
    """Runs on AWS Lambda.

    ``event`` must be a ``dict`` similar to the following:

    .. code-block:: python

        {
            'username': '<username>',
            'bearerUsername': '<authenticated-username>',
            'body': {
                'type': '<object-type>'
            }
        }

    ``body`` may be any Activity Streams object.

    :raises ForbiddenError: if ``username`` and ``bearerUsername`` do not match.

    :raises NotFoundError: if ``username`` is not found in the user table.

    :raises BadRequestError: if ``body`` is not an Activity Streams object.

    :raises TooManyAccessError: if there are too many access.
    """
    LOGGER.debug('receiving outbound object: %s', event)
    username = event['username']
    bearer_username = event['bearerUsername']
    if username != bearer_username:
        raise ForbiddenError('username and bearerUsername do not match')

    LOGGER.debug('looking up the user: %s', username)
    user = USER_TABLE.find_user_by_username(username)
    if user is None:
        raise NotFoundError(f'no such user: {username}')

    try:
        LOGGER.debug('loading body: %s', event['body'])
        body = DictObject(event['body'])
    except (TypeError, ValueError) as exc:
        raise BadRequestError(f'invalid body: {exc}') from exc

    object_key = {
        'bucket': OBJECTS_BUCKET_NAME,
        'key': user.generate_staging_outbox_key(),
    }
    save_object(boto3.client('s3'), object_key, body)

    return {}
