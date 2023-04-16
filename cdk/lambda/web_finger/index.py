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
from libmumble.exceptions import (
    BadConfigurationError,
    BadRequestError,
    NotFoundError,
    UnexpectedDomainError,
)


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

DOMAIN_NAME = os.environ.get('DOMAIN_NAME')


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

    :raises BadConfigurationError: if the domain name of the Mumble endpoints
    API is not configured.
    """
    LOGGER.debug('handling a WebFinger request: %s', event)
    host_domain_name = DOMAIN_NAME or event.get('apiDomainName')
    LOGGER.debug('Mumble endpoints API domain name: %s', host_domain_name)
    if not host_domain_name:
        raise BadConfigurationError(
            'Mumble endpoints API domain name must be configured',
        )
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
