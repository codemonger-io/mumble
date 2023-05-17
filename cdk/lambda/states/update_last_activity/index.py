# -*- coding: utf-8 -*-

"""Updates the last activity timestamp of a given user.

You have specify the following environment variables:
* ``USER_TABLE_NAME``: name of the DynamoDB table that manages user information.
* ``DOMAIN_NAME_PARAMETER_PATH``: path to the parameter storing the domain name
  in Parameter Store on AWS Systems Manager.
"""

import logging
import os
import boto3
from libmumble.exceptions import BadConfigurationError, NotFoundError
from libmumble.id_scheme import split_user_id
from libmumble.parameters import get_domain_name
from libmumble.user_table import UserTable


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

DOMAIN_NAME = get_domain_name(boto3.client('ssm'))

USER_TABLE_NAME = os.environ['USER_TABLE_NAME']
USER_TABLE = UserTable(boto3.resource('dynamodb').Table(USER_TABLE_NAME))


def lambda_handler(event, _context):
    """Runs on AWS Lambda.

    ``event`` must be a ``dict`` similar to the following:

    .. code-block:: python

        {
            'actor': {
                'id': '<actor-id>'
            }
        }

    :raises KeyError: if ``event`` lacks any mandatory property.

    :raises BadConfigurationError: if the domain name in the actor ID is not
    the configured one.

    :raises NotFoundError: if the actor is not found in the user table.

    :raises TooManyAccessError: if access to the DynamoDB table exceeds the
    limit.
    """
    LOGGER.debug('updating last activity: %s', event)
    actor_id = event['actor']['id']
    domain_name, username, _ = split_user_id(actor_id)
    if domain_name != DOMAIN_NAME:
        raise BadConfigurationError(
            f'domain name mismatch: {DOMAIN_NAME} vs {domain_name}',
        )
    user = USER_TABLE.find_user_by_username(username, DOMAIN_NAME)
    if user is None:
        raise NotFoundError(f'no such user: {username}')
    user.update_last_activity()
