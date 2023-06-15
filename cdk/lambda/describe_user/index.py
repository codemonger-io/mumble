# -*- coding: utf-8 -*-

"""Describes a given user.

You must specify the following environment variable:
* ``USER_TABLE_NAME``: name of the DynamoDB table storing user information.
* ``DOMAIN_NAME_PARAMETER_PATH``: path to the parameter that stores the domain
  name in Parameter Store on AWS Systems Manager.
"""

import logging
import os
from typing import Any, Dict
import boto3
from libmumble.exceptions import NotFoundError
from libmumble.parameters import get_domain_name
from libmumble.user_table import User, UserTable


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

DOMAIN_NAME = get_domain_name(boto3.client('ssm'))

# user table
USER_TABLE_NAME = os.environ['USER_TABLE_NAME']
USER_TABLE = UserTable(boto3.resource('dynamodb').Table(USER_TABLE_NAME))


def describe_user(user: User) -> Dict[str, Any]:
    """Describes a given user.
    """
    return {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': user.id,
        'type': 'Person',
        'name': user.name,
        'preferredUsername': user.preferred_username,
        'summary': user.summary,
        'url': user.url,
        'inbox': user.inbox_uri,
        'outbox': user.outbox_uri,
        'followers': user.followers_uri,
        'following': user.following_uri,
        'publicKey': user.public_key,
    }


def lambda_handler(event, _context):
    """Runs on AWS Lambda.

    ``event`` must be a ``dict`` similar to the following:

    .. code-block:: python

        {
            'username': '<username>',
        }

    :raises NotFoundError: if no user is assocaited with ``username``.

    :raises TooManyAccessError: if there are too many requests.
    """
    LOGGER.debug('describing a user: %s', event)
    username = event['username']

    LOGGER.debug('looking up user: %s', username)
    user = USER_TABLE.find_user_by_username(username, DOMAIN_NAME)
    if user is None:
        raise NotFoundError(f'no such user: {username}')

    return describe_user(user)
