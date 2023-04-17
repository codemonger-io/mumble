# -*- coding: utf-8 -*-

"""Describes a given user.

You must specify the following environment variable:
* ``USER_TABLE_NAME``: name of the DynamoDB table storing user information.

You must specify the following environment variable in production:
* ``DOMAIN_NAME``: domain name of the Mumble endpoints API. used to generate
  URIs. the ``apiDomainName`` property in an incoming event is used if omitted.
"""

from functools import cached_property
import logging
import os
from typing import Any, Dict, Optional, TypedDict
import boto3
from libmumble.exceptions import (
    BadConfigurationError,
    CorruptedDataError,
    NotFoundError,
    TooManyAccessError,
)


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

DOMAIN_NAME: Optional[str] = os.environ.get('DOMAIN_NAME')

# user table
dynamodb = boto3.resource('dynamodb')
USER_TABLE_NAME = os.environ['USER_TABLE_NAME']
USER_TABLE = dynamodb.Table(USER_TABLE_NAME)


class PublicKey(TypedDict):
    """Public key information.
    """
    id: str
    owner: str
    publicKeyPem: str


class User: # pylint: disable=too-many-instance-attributes
    """User information.
    """
    domain_name: str
    username: str
    name: str
    preferred_username: str
    summary: str
    url: str
    public_key_pem: str
    """PEM representation of the public key."""
    private_key_path: str
    """Path to the private key in Parameter Store on AWS Systems Manager."""

    def __init__( # pylint: disable=too-many-arguments
        self,
        domain_name: str,
        username: str,
        name: str,
        preferred_username: str,
        summary: str,
        url: str,
        public_key_pem: str,
        private_key_path: str,
    ):
        """Initializes with given parameters.
        """
        self.domain_name = domain_name
        self.username = username
        self.name = name
        self.preferred_username = preferred_username
        self.summary = summary
        self.url = url
        self.public_key_pem = public_key_pem
        self.private_key_path = private_key_path

    @staticmethod
    def parse_item(item: Dict[str, Any], domain_name: str) -> 'User':
        """Parses a given item in the user table.

        ``item`` must be a ``dict`` similar to the following (other items are
        ignored):

        .. code-block:: python

            {
                'pk': 'user:<username>',
                'name': '<name>',
                'preferredUsername': '<preferred-username>',
                'summary': '<summary>',
                'url': '<url>',
                'publicKeyPem': '<public-key-pem>',
                'privateKeyPath': '<private-key-path>'
            }

        :raises ValueError: if ``item`` is not valid.
        """
        try:
            username = parse_user_partition_key(item['pk'])
            return User(
                domain_name=domain_name,
                username=username,
                name=item['name'],
                preferred_username=item['preferredUsername'],
                summary=item['summary'],
                url=item['url'],
                public_key_pem=item['publicKeyPem'],
                private_key_path=item['privateKeyPath'],
            )
        except KeyError as exc:
            raise ValueError(f'invalid user item: {exc}') from exc

    @property
    def id(self) -> str: # pylint: disable=invalid-name
        """ID of the user.
        """
        return f'https://{self.domain_name}/users/{self.username}'

    @property
    def inbox_uri(self) -> str:
        """URI of the inbox.
        """
        return f'{self.id}/inbox'

    @property
    def outbox_uri(self) -> str:
        """URI of the outbox.
        """
        return f'{self.id}/outbox'

    @property
    def followers_uri(self) -> str:
        """URI of the followers list.
        """
        return f'{self.id}/followers'

    @property
    def following_uri(self) -> str:
        """URI of the following list.
        """
        return f'{self.id}/following'

    @cached_property
    def public_key(self) -> PublicKey:
        """Public key information of the user.
        """
        return {
            'id': f'{self.id}#main-key',
            'owner': self.id,
            'publicKeyPem': self.public_key_pem,
        }


def find_user_by_username(username: str, domain_name: str) -> Optional[User]:
    """Finds a user by a given username.

    :returns: ``None`` if no user is associated with ``username``.

    :raises CorruptedDataError: if the user data is corrupted.

    :raises TooManyAccessError: if access to the DynamoDB table exceeds the
    limit.
    """
    exceptions = dynamodb.meta.client.exceptions
    try:
        res = USER_TABLE.get_item(Key=make_user_primary_key(username))
    except exceptions.ProvisionedThroughputExceededException as exc:
        raise TooManyAccessError(
            'exceeded provisioned table throughput',
        ) from exc
    except exceptions.RequestLimitExceeded as exc:
        raise TooManyAccessError('exceeded API access limit') from exc
    if 'Item' not in res:
        return None
    try:
        return User.parse_item(res['Item'], domain_name)
    except ValueError as exc:
        raise CorruptedDataError(
            f'invalid user data: "{username}"',
        ) from exc


def make_user_primary_key(username: str) -> Dict[str, str]:
    """Returns a primary key to get a user from the user table.
    """
    return {
        'pk': f'user:{username}',
        'sk': 'reserved',
    }


def parse_user_partition_key(pk: str) -> str: # pylint: disable=invalid-name
    """Returns a given partition key of a user.

    :returns: username in ``pk``.

    :raises ValueError: if ``pk`` is invalid.
    """
    prefix = 'user:'
    if not pk.startswith(prefix):
        raise ValueError(f'partition key must start with "{prefix}"')
    return pk[len(prefix):]


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

    :raises CorruptedDataError: if the stored data is corrupted.

    :raises TooManyAccessError: if there are too many requests.
    """
    LOGGER.debug('describing a user: %s', event)
    domain_name = DOMAIN_NAME or event.get('apiDomainName')
    LOGGER.debug('Mumble endpoints API domain name: %s', domain_name)
    if not domain_name:
        raise BadConfigurationError(
            'Mumble endpoints API domain name must be configured',
        )
    username = event['username']
    LOGGER.debug('looking up user: %s', username)
    user = find_user_by_username(username, domain_name)
    if user is None:
        raise NotFoundError(f'no such user: {username}')
    return {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': user.id,
        'type': 'Person',
        # TODO: do not hard-code
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
