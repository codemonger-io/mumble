# -*- coding: utf-8 -*-

"""Provides access to the user table.
"""

from functools import cached_property
import logging
from typing import Any, Dict, Optional, TypedDict
from libactivitypub.actor import PublicKey
from .exceptions import CorruptedDataError, TooManyAccessError


LOGGER = logging.getLogger('libmumble.user_table')
LOGGER.setLevel(logging.DEBUG)


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
            username = UserTable.parse_partition_key(item['pk'])
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


class UserTableKey(TypedDict):
    """Primary key of the user table.
    """
    pk: str
    sk: str


class UserTable:
    """User table.
    """
    PK_PREFIX = 'user:'
    """Prefix of a partition key."""

    def __init__(self, table: Any):
        """Wraps a given DynamoDB table that stores user information.

        :params boto3.DynamoDB.Table: DynamoDB Table resource of the user
        table.
        """
        self._table = table

    def find_user_by_username(
        self,
        username: str,
        domain_name: str,
    ) -> Optional[User]:
        """Finds a user associated with a given username.

        :returns: ``None`` if no user is associated with ``username``.

        :raises CorruptedDataError: if the user data is corrupted.

        :raises TooManyAccessError: if access to the DynamoDB table exceeds the
        limit.
        """
        exceptions = self._table.meta.client.exceptions
        try:
            key = UserTable.make_primary_key(username)
            res = self._table.get_item(Key=key)
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

    @staticmethod
    def make_primary_key(username: str) -> UserTableKey:
        """Returns a primary key to get a user from the user table.
        """
        return {
            'pk': f'{UserTable.PK_PREFIX}{username}',
            'sk': 'reserved',
        }

    @staticmethod
    def parse_partition_key(pk: str) -> str: # pylint: disable=invalid-name
        """Returns a given partition key of a user.

        :returns: username in ``pk``.

        :raises ValueError: if ``pk`` is invalid.
        """
        if not pk.startswith(UserTable.PK_PREFIX):
            raise ValueError(
                f'partition key must start with "{UserTable.PK_PREFIX}"',
            )
        return pk[len(UserTable.PK_PREFIX):]
