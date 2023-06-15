# -*- coding: utf-8 -*-

"""Responds to a WebFinger request.

You have to specify the following environment variables:
* ``USER_TABLE_NAME``: name of the DynamoDB table that manages user information.
* ``DOMAIN_NAME_PARAMETER_PATH``: path to the parameter that stores the domain
  name in Parameter Store on AWS Systems Manager.
"""

import logging
import os
import boto3
from libactivitypub.utils import parse_acct_uri
from libmumble.exceptions import (
    BadRequestError,
    NotFoundError,
    UnexpectedDomainError,
)
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
            'resource': '<account>',
        }

    Returns a ``dict`` similar to the following:

    .. code-block:: python

        {
            'subject': '<account>',
            'links': [
                {
                    'rel': 'self',
                    'type': 'application/activity+json',
                    'href': '<actor-uri>'
                }
            ]
        }

    :raises KeyError: if no ``resource`` is specified, or if ``apiDomainName``
    is not specified when ``DOMAIN_NAME`` is ``None``.

    :raises BadRequestError: if ``resource`` is invalid.

    :raises UnexpectedDomainError: if the domain name of the requested entity
    dot not match the domain name of the Mumble API.

    :raises NotFoundError: if the account is not found.

    :raises TooManyAccessError: if there are too many requests.
    """
    LOGGER.debug('handling a WebFinger request: %s', event)
    try:
        username, domain_name = parse_acct_uri(event['resource'])
    except ValueError as exc:
        raise BadRequestError(f'{exc}') from exc
    if domain_name != DOMAIN_NAME:
        raise UnexpectedDomainError(f'unexpected domain name: {domain_name}')

    LOGGER.debug('looking up user: %s', username)
    user = USER_TABLE.find_user_by_username(username, DOMAIN_NAME)
    if user is None:
        raise NotFoundError(f'no such user: {username}')

    return {
        'subject': f'{username}@{domain_name}',
        'links': [
            {
                'rel': 'self',
                'type': 'application/activity+json',
                'href': user.id,
            },
        ],
    }
