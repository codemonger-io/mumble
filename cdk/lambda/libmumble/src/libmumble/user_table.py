# -*- coding: utf-8 -*-

"""Provides access to the user table.
"""

from functools import cached_property
import logging
import re
from typing import Any, Dict, Optional, Tuple
from urllib.parse import unquote, urlparse
from boto3.dynamodb.conditions import Attr
from libactivitypub.activity import Follow
from libactivitypub.actor import PublicKey
from .exceptions import CorruptedDataError, TooManyAccessError
from .utils import current_yyyymmdd_hhmmss_ssssss


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


class UserTable:
    """User table.
    """
    USER_PK_PREFIX = 'user:'
    """Prefix of a partition key to query a user."""
    FOLLOWER_PK_PREFIX = 'follower:'
    """Prefix of a partition key to query followers."""

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
        try:
            key = UserTable.make_user_key(username)
            res = self._table.get_item(Key=key)
        except self.exceptions.ProvisionedThroughputExceededException as exc:
            raise TooManyAccessError(
                'exceeded provisioned table throughput',
            ) from exc
        except self.exceptions.RequestLimitExceeded as exc:
            raise TooManyAccessError('exceeded API access limit') from exc
        if 'Item' not in res:
            return None
        try:
            return User.parse_item(res['Item'], domain_name)
        except ValueError as exc:
            raise CorruptedDataError(
                f'invalid user data: "{username}"',
            ) from exc

    def add_user_follower(self, username: str, follow: Follow):
        """Adds a follower of a given user.

        :param Follow follow: "Follow" activity.

        :raises ValueError: if the object of ``follow`` is not the specified
        user.

        :raises TooManyAccessError: if access to the DynamoDB table exceeds
        the limit.
        """
        if get_username_from_user_id(follow.followed_id) != username:
            raise ValueError(
                f'follow request in wrong inbox: {follow.followed_id},'
                f' inbox={username}',
            )
        item = UserTable.make_follower_key(username, follow.actor_id)
        item.update({
            'createdAt': current_yyyymmdd_hhmmss_ssssss(),
            'updatedAt': current_yyyymmdd_hhmmss_ssssss(),
            'followerId': follow.actor_id,
            'followActivityId': follow.id,
            # TODO: sharedInboxId?
        })
        try:
            LOGGER.debug(
                'putting follower: username=%s, follower=%s',
                username,
                follow.actor_id,
            )
            self._table.put_item(
                Item=item,
                ConditionExpression=Attr('pk').not_exists(),
            )
            # increments the number of followers
            LOGGER.debug('incrementing follower count')
            res = self._table.update_item(
                Key=UserTable.make_user_key(username),
                AttributeUpdates={
                    'followerCount': {
                        'Value': 1,
                        'Action': 'ADD',
                    },
                },
                ReturnValues='UPDATED_NEW',
            )
            LOGGER.debug(
                'new follower count: %d',
                res['Attributes'].get('followerCount'),
            )
        except self.exceptions.ConditionalCheckFailedException:
            LOGGER.debug('existing follower')
            # follower count should stay
        except self.exceptions.ProvisionedThroughputExceededException as exc:
            raise TooManyAccessError(
                'exceeded provisioned table throughput',
            ) from exc
        except self.exceptions.RequestLimitException as exc:
            raise TooManyAccessError('exceeded API access limit') from exc


    @staticmethod
    def make_user_key(username: str) -> Dict[str, Any]:
        """Returns a primary key to get a user from the user table.
        """
        return {
            'pk': f'{UserTable.USER_PK_PREFIX}{username}',
            'sk': 'reserved',
        }

    @staticmethod
    def make_follower_key(username: str, follower_id: str) -> Dict[str, Any]:
        """Returns a primary key to get a follower from the user table.
        """
        return {
            'pk': f'{UserTable.FOLLOWER_PK_PREFIX}{username}',
            'sk': follower_id,
        }

    @staticmethod
    def parse_partition_key(pk: str) -> str: # pylint: disable=invalid-name
        """Returns a given partition key of a user.

        :returns: username in ``pk``.

        :raises ValueError: if ``pk`` is invalid.
        """
        if not pk.startswith(UserTable.USER_PK_PREFIX):
            raise ValueError(
                f'partition key must start with "{UserTable.USER_PK_PREFIX}"',
            )
        return pk[len(UserTable.USER_PK_PREFIX):]

    @property
    def exceptions(self):
        """Module containing exceptions from the DynamoDB client.
        """
        return self._table.meta.client.exceptions


def parse_user_id(user_id: str) -> Tuple[str, str]:
    """Parses a given user ID.

    :returns: tuple of domain name and username.

    :raises ValueError: ``user_id`` does not represent a user ID in this
    service.
    """
    parsed = urlparse(user_id)
    if not parsed.hostname:
        raise ValueError(f'no domain name: {user_id}')
    path = unquote(parsed.path).rstrip('/')
    match = re.match(r'^\/users\/([^/]+)$', path)
    if match is None:
        raise ValueError(f'not a user ID: {user_id}')
    return parsed.hostname, match.group(1)


def get_username_from_user_id(user_id: str) -> str:
    """Extracts the username from a given user ID.

    :param str user_id: like "https://<domain-name>/users/{username}".

    :raises ValueError: ``user_id`` does not represent a user ID in this
    service.
    """
    _, username = parse_user_id(user_id)
    return username
