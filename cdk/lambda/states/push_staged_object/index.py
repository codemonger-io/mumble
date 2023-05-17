# -*- coding: utf-8 -*-

"""Pushes a staged object into the object table.

You have to specify the following environment variables:
* ``OBJECT_TABLE_NAME``: name of the DynamoDB table that manages objects.
* ``OBJECTS_BUCKET_NAME``: name of the S3 bucket that stores objects.
"""

import logging
import os
import boto3
from libactivitypub.data_objects import Note
from libactivitypub.objects import DictObject
from libmumble.object_table import ObjectTable
from libmumble.objects_store import dict_as_object_key, load_object


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

OBJECTS_BUCKET_NAME = os.environ['OBJECTS_BUCKET_NAME']

OBJECT_TABLE_NAME = os.environ['OBJECT_TABLE_NAME']
OBJECT_TABLE = ObjectTable(boto3.resource('dynamodb').Table(OBJECT_TABLE_NAME))


def push_object(obj: DictObject):
    """Pushes a given object into the object table.

    :raises TypeError: if ``obj`` is not able to be pushed to the object table.

    :raises DuplicateItemError: if ``obj`` is already in the object table.

    :raises TooManyAccessError: if access to the DynamoDB table exceeds the
    limit.
    """
    if obj.type == 'Note':
        OBJECT_TABLE.put_post(obj.cast(Note))
    else:
        raise TypeError(f'"{obj.type}" cannot be pushed to the object table')


def lambda_handler(event, _context):
    """Runs on AWS Lambda.

    ``event`` must be a ``dict`` similar to the following:

    .. code-block:: python

        {
            'object': {
                'bucket': '<bucket-name>',
                'key': '<object-key>'
            }
        }

    :raises ValueError: if the loaded object is invalid.

    :raises TypeError: if ``object`` is invalid,
    or if the loaded object is invalid.

    :raises NotFoundError: if the object is not found.

    :raises DuplicateItemError: if the object is already in the object table.

    :raises TooManyRequestError: if access to the DynamoDB table exceeds the
    limit.
    """
    LOGGER.debug('pushing staged object: %s', event)
    object_key = dict_as_object_key(event['object'])
    LOGGER.debug('loading object: %s', object_key)
    obj = load_object(boto3.client('s3'), object_key)
    push_object(obj)
