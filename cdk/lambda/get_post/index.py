# -*- coding: utf-8 -*-

"""Returns a specified post object of a given user.

You have to specify the following environment variables:
* ``OBJECT_TABLE_NAME``: name of the DynamoDB table that manages objects.
* ``OBJECTS_BUCKET_NAME``: name of the S3 bucket that contains objects.
* ``DOMAIN_NAME_PARAMETER_PATH``: path to the parameter storing the domain name
  in Parameter Store on AWS Systems Manager.
"""

import logging
import os
import boto3
from libmumble.exceptions import CorruptedDataError, NotFoundError
from libmumble.object_table import ObjectTable
from libmumble.parameters import get_domain_name


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

DOMAIN_NAME = get_domain_name(boto3.client('ssm'))

OBJECTS_BUCKET_NAME = os.environ['OBJECTS_BUCKET_NAME']

OBJECT_TABLE_NAME = os.environ['OBJECT_TABLE_NAME']
OBJECT_TABLE = ObjectTable(boto3.resource('dynamodb').Table(OBJECT_TABLE_NAME))


def lambda_handler(event, _context):
    """Runs on AWS Lambda.

    ``event`` must be a ``dict`` similar to the following:

    .. code-block:: python

        {
            'username': '<username>',
            'uniquePart': '<unique-part>'
        }

    :raises NotFoundError: if the user is not found,
    or if the post object is not found,
    or if the post object is not public.

    :raises CorruptedDataError: if the object is not found in the objects
    bucket.
    """
    LOGGER.debug('obtaining post: %s', event)
    username = event['username']
    unique_part = event['uniquePart']
    LOGGER.debug(
        'looking up post: username=%s, unique part=%s',
        username,
        unique_part,
    )
    meta_post = OBJECT_TABLE.find_user_post(username, unique_part)
    if meta_post is None or not meta_post.is_public:
        raise NotFoundError(
            f'no such object: user={username}, id={unique_part}',
        )
    try:
        post = meta_post.resolve(boto3.client('s3'), OBJECTS_BUCKET_NAME)
    except NotFoundError as exc:
        raise CorruptedDataError(f'{exc}') from exc
    return post.to_dict()
