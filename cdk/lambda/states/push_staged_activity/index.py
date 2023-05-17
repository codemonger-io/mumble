# -*- coding: utf-8 -*-

"""Pushes a staged activity into the object table.

You have to specify the following environment variables:
* ``OBJECT_TABLE_NAME``: name of the DynamoDB table that manages objects.
* ``OBJECTS_BUCKET_NAME``: name of the S3 bucket that stores objects.
"""

import logging
import os
import boto3
from libmumble.exceptions import BadConfigurationError
from libmumble.object_table import ObjectTable
from libmumble.objects_store import dict_as_object_key, load_activity


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

OBJECTS_BUCKET_NAME = os.environ['OBJECTS_BUCKET_NAME']

OBJECT_TABLE_NAME = os.environ['OBJECT_TABLE_NAME']
OBJECT_TABLE = ObjectTable(boto3.resource('dynamodb').Table(OBJECT_TABLE_NAME))


def lambda_handler(event, _context):
    """Runs on AWS Lambda.

    ``event`` must be a ``dict`` similar to the following:

    .. code-block:: python

        {
            'activity': {
                'bucket': '<bucket-name>',
                'key': '<object-key>'
            }
        }

    Returns a ``dict`` similar to the following:

    .. code-block:: python

        {
            'actor': '<actor-id>'
        }

    :raises KeyError: if ``event`` lacks any mandatory key.

    :raises TypeError: if ``event['activity']`` is an invalid object key.

    :raises ValueError: if the loaded activity is invalid.

    :raises BadConfigrationError: if ``event['activity']['bucket']`` does not
    match the configured objects bucket.

    :raises TooManyAccessError: if access to the DynamoDB table exceeds the
    limit.

    :raises DuplicateItemError: if the activity already exists in the object
    table.
    """
    LOGGER.debug('pushing staged activity: %s', event)
    object_key = dict_as_object_key(event['activity'])
    if object_key['bucket'] != OBJECTS_BUCKET_NAME:
        raise BadConfigurationError(
            'objects bucket mismatch:'
            f' expected={OBJECTS_BUCKET_NAME}, given={object_key["bucket"]}',
        )
    LOGGER.debug('loading activity: %s', object_key)
    activity = load_activity(boto3.client('s3'), object_key)
    LOGGER.debug('pushing activity: %s', activity.id)
    OBJECT_TABLE.put_activity(activity)
    return {
        'actor': activity.actor_id,
    }
