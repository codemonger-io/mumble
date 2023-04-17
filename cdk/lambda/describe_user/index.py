# -*- coding: utf-8 -*-

"""Describes a given user.

You must specify the following environment variable in production:
* ``DOMAIN_NAME``: domain name of the Mumble endpoints API. used to generate
  URIs. the ``apiDomainName`` property in an incoming event is used if omitted.
"""

import logging
import os
from typing import Optional
from libmumble.exceptions import BadConfigurationError, NotFoundError


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

DOMAIN_NAME: Optional[str] = os.environ.get('DOMAIN_NAME')


def lambda_handler(event, _context):
    """Runs on AWS Lambda.

    ``event`` must be a ``dict`` similar to the following:

    .. code-block:: python

        {
            'username': '<username>',
            'apiDomainName': '<domain-name>'
        }

    :raises NotFoundError: if no user is assocaited with ``username``.

    :raises BadConfigurationError: if the domain name of the Mumble endpoints
    API is not configured.
    """
    LOGGER.debug('describing a user: %s', event)
    domain_name = DOMAIN_NAME or event.get('apiDomainName')
    LOGGER.debug('Mumble endpoints API domain name: %s', domain_name)
    if not domain_name:
        raise BadConfigurationError(
            'Mumble endpoints API domain name must be configured',
        )
    username = event['username']
    if username != 'kemoto':
        raise NotFoundError(f'no such user: {username}')
    user_uri = f'https://{domain_name}/users/{username}'
    return {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': user_uri,
        'type': 'Person',
        # TODO: do not hard-code
        'name': 'Kikuo Emoto',
        'preferredUsername': 'kemoto',
        'summary': 'The representative of codemonger.',
        'url': 'https://codemonger.io',
        'inbox': f'{user_uri}/inbox',
        'outbox': f'{user_uri}/outbox',
        'followers': f'{user_uri}/followers',
        'following': f'{user_uri}/following',
        'publicKey': {
            'id': f'{user_uri}#main-key',
            'owner': user_uri,
            # TODO: load the public key
            'publicKeyPem': '-----BEGIN PUBLIC KEY----\n...',
        },
    }
