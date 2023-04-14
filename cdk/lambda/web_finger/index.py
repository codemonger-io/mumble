# -*- coding: utf-8 -*-

"""Responds to a WebFinger request.

You can specify the following optional environment variable,
* ``DOMAIN_NAME``: domain name of the Mumble server. accounts that are not in
  this domain will be rejected. the API domain name in an input event is used
  if omitted.
  MUST BE SPECIFIED in production.
"""

import logging
import os
from libactivitypub.utils import parse_acct_uri


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

DOMAIN_NAME = os.environ.get('DOMAIN_NAME')


class MumbleBaseException(Exception):
    """Base exception.
    """
    message: str
    """Brief explanation about the problem."""

    def __init__(self, message: str):
        """Initializes with a given message.
        """
        self.message = message

    def __str__(self):
        class_name = type(self).__name__
        return f'{class_name}({self.message})'

    def __rerp__(self):
        class_name = type(self).__name__
        return f'{class_name}({repr(self.message)})'


class BadRequestError(MumbleBaseException):
    """Raised if the request is invalid.
    """


class UnexpectedDomainError(MumbleBaseException):
    """Raised if the domain name is unexpected.
    """


class NotFoundError(MumbleBaseException):
    """Raised if the account is not found.
    """


def parse_resource(resource: str) -> str:
    """Parses a given "resource" query parameter.

    Revmoes the prefix "acct:" from ``resource``.

    :raises BadRequestError: if ``resource`` does not start with "acct:".
    """
    prefix = 'acct:'
    if not resource.startswith(prefix):
        raise BadRequestError('resource must start with "{prefix}": resource')
    return resource[len(prefix):]


def lambda_handler(event, _context):
    """Runs on AWS Lambda.

    ``event`` must be a ``dict`` similar to the following:

    .. code-block:: python

        {
            'resource': '<account>',
            'apiDomainName': '<domain-name>'
        }

    ``apiDomainName`` is the full domain name used to invoke the API.
    This parameter can be used to verify the requested account resides in the
    domain, if ``DOMAIN_NAME`` environment variable is not defined.

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

    :raises InvalidDomainError: if the domain name in ``resource`` does not
    match the domain name that this function supposes.

    :raises NotFoundError: if the account is not found.
    """
    LOGGER.debug('handling a WebFinger request: %s', event)
    host_domain_name = DOMAIN_NAME or event['apiDomainName']
    try:
        name, domain_name = parse_acct_uri(event['resource'])
    except ValueError as exc:
        raise BadRequestError(f'{exc}') from exc
    if domain_name != host_domain_name:
        raise UnexpectedDomainError(f'unexpected domain name: {domain_name}')
    # TODO: do not hard-code
    if name != 'kemoto':
        raise NotFoundError(f'no such user: {name}')
    # TODO: do not hard-code
    return {
        'subject': f'{name}@{domain_name}',
        'links': [
            {
                'rel': 'self',
                'type': 'application/activity+json',
                'href': f'https://{host_domain_name}/users/{name}',
            },
        ],
    }
