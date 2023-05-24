# -*- coding: utf-8 -*-

"""Provides access to the user table.
"""

from datetime import datetime
from functools import cached_property
import logging
import re
from typing import Any, Dict, Generator, Optional, Tuple
from urllib.parse import unquote, urlparse
from boto3.dynamodb.conditions import Attr, Key
from libactivitypub.activity import Follow
from libactivitypub.actor import PublicKey
from .dynamodb import TableWrapper
from .exceptions import (
    BadConfigurationError,
    CorruptedDataError,
    NotFoundError,
    TooManyAccessError,
)
from .id_scheme import (
    generate_user_activity_id,
    generate_user_post_id,
    make_user_followers_uri,
    make_user_following_uri,
    make_user_id,
    make_user_inbox_uri,
    make_user_key_id,
    make_user_outbox_uri,
)
from .objects_store import generate_user_staging_outbox_key
from .utils import current_yyyymmdd_hhmmss_ssssss, parse_yyyymmdd_hhmmss_ssssss


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
    follower_count: int
    following_count: int
    created_at: datetime
    updated_at: datetime
    last_activity_at: datetime

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
        follower_count: int,
        following_count: int,
        created_at: datetime,
        updated_at: datetime,
        last_activity_at: datetime,
        table: Optional['UserTable']=None,
    ):
        """Initializes with given parameters.

        :param Optional[UserTable] table: ``UserTable`` that stores the user.
        optional, though, some operation on ``User`` needs this.
        """
        self.domain_name = domain_name
        self.username = username
        self.name = name
        self.preferred_username = preferred_username
        self.summary = summary
        self.url = url
        self.public_key_pem = public_key_pem
        self.private_key_path = private_key_path
        self.follower_count = follower_count
        self.following_count = following_count
        self.created_at = created_at
        self.updated_at = updated_at
        self.last_activity_at = last_activity_at
        self._table = table

    @staticmethod
    def parse_item(
        item: Dict[str, Any],
        domain_name: str,
        table: Optional['UserTable']=None,
    ) -> 'User':
        """Parses a given item in the user table.

        ``item`` must be a ``dict`` similar to the following (other keys are
        ignored):

        .. code-block:: python

            {
                'pk': 'user:<username>',
                'name': '<name>',
                'preferredUsername': '<preferred-username>',
                'summary': '<summary>',
                'url': '<url>',
                'publicKeyPem': '<public-key-pem>',
                'privateKeyPath': '<private-key-path>',
                'followerCount': 123,
                'followingCount': 123,
                'createdAt': '<yyyy-mm-ddTHH:MM:ss.SSSSSSZ>',
                'updatedAt': '<yyyy-mm-ddTHH:MM:ss.SSSSSSZ>',
                'lastActivityAt': '<yyyy-mm-ddTHH:MM:ss.SSSSSSZ>'
            }

        :param Optional[UserTable] table: ``UserTable`` that stores the user.
        optional, though, some operation on ``User`` needs this.

        :raises ValueError: if ``item`` is invalid.

        :raises KeyError: if ``item`` lacks mandatory properties.

        :raises TypeError: if ``item`` is invalid.
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
                follower_count=int(item['followerCount']),
                following_count=int(item['followingCount']),
                created_at=parse_yyyymmdd_hhmmss_ssssss(item['createdAt']),
                updated_at=parse_yyyymmdd_hhmmss_ssssss(item['updatedAt']),
                last_activity_at=parse_yyyymmdd_hhmmss_ssssss(item['lastActivityAt']),
                table=table,
            )
        except KeyError as exc:
            raise ValueError(f'invalid user item: {exc}') from exc

    @property
    def id(self) -> str: # pylint: disable=invalid-name
        """ID of the user.
        """
        return make_user_id(self.domain_name, self.username)

    @property
    def inbox_uri(self) -> str:
        """URI of the inbox.
        """
        return make_user_inbox_uri(self.id)

    @property
    def outbox_uri(self) -> str:
        """URI of the outbox.
        """
        return make_user_outbox_uri(self.id)

    @property
    def followers_uri(self) -> str:
        """URI of the followers list.
        """
        return make_user_followers_uri(self.id)

    @property
    def following_uri(self) -> str:
        """URI of the following list.
        """
        return make_user_following_uri(self.id)

    def enumerate_followers(
        self,
        items_per_query: int,
        after: Optional[str]=None,
        before: Optional[str]=None,
    ) -> Generator[str, None, None]:
        """Enumerates the follower of the user.

        :param int items_per_query: maximum number of items to be fetched in
        a single DynamoDB query. NOT the total number of followers to be
        fetched.

        :returns: generator of follower IDs.

        :raises AttributeError: if this user is not associated with the user
        table.

        :raises ValueError: if both of ``after`` and ``before`` are specified.

        :raises TooManyAccessError: if access to the DynamoDB table exceeds
        the limit.
        """
        if self._table is None:
            raise AttributeError('no user table is associated')
        return self._table.enumerate_user_followers(
            self.username,
            items_per_query,
            after=after,
            before=before,
        )

    def enumerate_following(
        self,
        items_per_query: int,
        after: Optional[str]=None,
        before: Optional[str]=None,
    ) -> Generator[str, None, None]:
        """Enumerates the accounts followed by the user.

        :param int items_per_query: maximum number of items to be fetched in
        a single DynamoDB query. NOT the total number of accounts to be
        fetched.

        :returns: generator of account IDs followed by the user.

        :raises AttributeError: if this user is not associated with the user
        table.

        :raises ValueError: if both of ``after`` and ``before`` are specified.

        :raises TooManyAccessError: if access to the DynamoDB table exceeds
        the limit.
        """
        if self._table is None:
            raise AttributeError('no user table is associated')
        return self._table.enumerate_user_following(
            self.username,
            items_per_query,
            after=after,
            before=before,
        )

    @cached_property
    def public_key(self) -> PublicKey:
        """Public key information of the user.
        """
        return {
            'id': self.key_id,
            'owner': self.id,
            'publicKeyPem': self.public_key_pem,
        }

    @property
    def key_id(self) -> str:
        """Key pair ID of the user.
        """
        return make_user_key_id(self.id)

    def get_private_key(self, ssm) -> str:
        """Obtains the private key of this user from Parameter Store on AWS
        Systems Manager.

        :param boto3.client('ssm') ssm: AWS Systems Manager client to access
        Parameter Store.

        :returns: PEM representation of the private key.

        :raises BadConfigurationError: if the private key does not exist in
        Parameter Store.
        """
        try:
            res = ssm.get_parameter(
                Name=self.private_key_path,
                WithDecryption=True,
            )
        except (
            ssm.exceptions.InvalidKeyId,
            ssm.exceptions.ParameterNotFound,
        ) as exc:
            raise BadConfigurationError(
                f'no private key: {self.private_key_path}',
            ) from exc
        return res['Parameter']['Value']

    def update_last_activity(self):
        """Updates the timestamp of the last activity of the user.

        :raises AttributeError: if no user table is associated with this user.

        :raises NotFoundError: if the user is not in the user table.

        :raises TooManyAccessError: if access to the DynamoDB table exceeds
        the limit.
        """
        if self._table is None:
            raise AttributeError('no user table is associated')
        self._table.update_last_user_activity(self.username)

    def generate_activity_id(self) -> str:
        """Generates a random ID for an activity of the user.
        """
        return generate_user_activity_id(self.id)

    def generate_post_id(self) -> str:
        """Generates a random ID for a post of the user.
        """
        return generate_user_post_id(self.id)

    def generate_staging_outbox_key(self) -> str:
        """Generates a random object key in user's staging outbox.
        """
        return generate_user_staging_outbox_key(self.username)


class UserTable(TableWrapper):
    """User table.
    """
    USER_PK_PREFIX = 'user:'
    """Prefix of a partition key to query a user."""
    FOLLOWER_PK_PREFIX = 'follower:'
    """Prefix of a partition key to query followers."""
    FOLLOWEE_PK_PREFIX = 'followee:'
    """Prefix of a partition key to query followees."""

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
        except self.ProvisionedThroughputExceededException as exc:
            raise TooManyAccessError(
                'exceeded provisioned table throughput',
            ) from exc
        except self.RequestLimitExceeded as exc:
            raise TooManyAccessError('exceeded API access limit') from exc
        if 'Item' not in res:
            return None
        try:
            return User.parse_item(res['Item'], domain_name, table=self)
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
        except self.ConditionalCheckFailedException:
            LOGGER.debug('existing follower')
            # follower count should stay
        except self.ProvisionedThroughputExceededException as exc:
            raise TooManyAccessError(
                'exceeded provisioned table throughput',
            ) from exc
        except self.RequestLimitExceeded as exc:
            raise TooManyAccessError('exceeded API access limit') from exc

    def remove_user_follower(self, username: str, follow: Follow):
        """Removes a follower of a given user.

        :raises ValueError: if the object of ``follow`` is not the specified
        user.
        """
        if get_username_from_user_id(follow.followed_id) != username:
            raise ValueError(
                f'unfollow request in wrong inbox: {follow.followed_id},'
                f' inbox={username}',
            )
        key = UserTable.make_follower_key(username, follow.actor_id)
        try:
            LOGGER.debug(
                'removing follower: username=%s, follower=%s',
                username,
                follow.actor_id,
            )
            res = self._table.delete_item(
                Key=key,
                ReturnValues='ALL_OLD',
                ConditionExpression=Attr('pk').exists(),
            )
            if res['Attributes'].get('followActivityId') != follow.id:
                LOGGER.warning(
                    'follow activity ID mismatch: %s != %s',
                    follow.id,
                    res['Attributes'].get('followActivityId'),
                )
            # decrements the number of followers
            LOGGER.debug('decrementing follower count')
            res = self._table.update_item(
                Key=UserTable.make_user_key(username),
                AttributeUpdates={
                    'followerCount': {
                        'Value': -1,
                        'Action': 'ADD',
                    },
                },
                ReturnValues='UPDATED_NEW',
            )
            LOGGER.debug(
                'new follower count: %d',
                res['Attributes'].get('followerCount'),
            )
        except self.ConditionalCheckFailedException:
            LOGGER.debug('non-existing follower')
            # follower cound should stay
        except self.ProvisionedThroughputExceededException as exc:
            raise TooManyAccessError(
                'exceeded provisioned table throughput',
            ) from exc
        except self.RequestLimitExceeded as exc:
            raise TooManyAccessError('exceeded API access limit') from exc

    def enumerate_user_followers(
        self,
        username: str,
        items_per_query: int,
        after: Optional[str]=None,
        before: Optional[str]=None,
    ) -> Generator[str, None, None]:
        """Enumerates the followers of a given user.

        :param int items_per_query: maximum number of items to be fetched in
        a single DynamoDB query. NOT the maximum number of followers to be
        enumearted.

        :returns: generator of follower IDs.

        :raises ValueError: if both of ``after`` and ``before`` are specified.

        :raises TooManyAccessError: if access to the DynamoDB table exceeds
        the limit.
        """
        if after is not None and before is not None:
            raise ValueError('both of after and before are specified')
        # loops until all the followers are exhausted
        key_condition = Key('pk').eq(
            UserTable.make_follower_partition_key(username),
        )
        exclusive_start_key: Dict[str, Any] = {}
        if before is not None:
            before_key = UserTable.make_follower_key(username, before)
            exclusive_start_key['ScanIndexForward'] = False
            exclusive_start_key['ExclusiveStartKey'] = before_key
        if after is not None:
            after_key = UserTable.make_follower_key(username, after)
            exclusive_start_key['ExclusiveStartKey'] = after_key
        while True:
            LOGGER.debug(
                'querying followers: username=%s, from=%s',
                username,
                exclusive_start_key,
            )
            try:
                res = self._table.query(
                    KeyConditionExpression=key_condition,
                    Limit=items_per_query,
                    **exclusive_start_key,
                )
                follower_ids = [item['followerId'] for item in res['Items']]
                if before is not None:
                    follower_ids.sort()
                for follower_id in follower_ids:
                    yield follower_id
                last_evaluated_key = res.get('LastEvaluatedKey')
                LOGGER.debug('LastEvaludatedKey: %s', last_evaluated_key)
                if not last_evaluated_key:
                    return # finishes enumeration
                exclusive_start_key['ExclusiveStartKey'] = last_evaluated_key
            except self.ProvisionedThroughputExceededException as exc:
                raise TooManyAccessError(
                    'exceeded provisioned table throughput',
                ) from exc
            except self.RequestLimitExceeded as exc:
                raise TooManyAccessError('exceeded API access limit') from exc

    def enumerate_user_following(
        self,
        username: str,
        items_per_query: int,
        after: Optional[str]=None,
        before: Optional[str]=None,
    ) -> Generator[str, None, None]:
        """Enumerates the accounts followed by a given user.

        :param int items_per_query: maximum number of items to be fetched in
        a single DynamoDB query. NOT the total number of accounts to be
        enumerated.

        :returns: generator of account IDs followed by the user.

        :raises ValueError: if both of ``after`` and ``before`` are specified.

        :raises TooManyAccessError: if access to the DynamoDB table exceeds
        the limit.
        """
        if after is not None and before is not None:
            raise ValueError('both of after and before are specified')
        # loops until all the followed accounts are exhausted
        key_condition = Key('pk').eq(make_followee_partition_key(username))
        exclusive_start_key = {}
        if before is not None:
            before_key = make_followee_key(username, before)
            exclusive_start_key['ExclusiveStartKey'] = before_key
            exclusive_start_key['ScanIndexForward'] = False
        elif after is not None:
            after_key = make_followee_key(username, after)
            exclusive_start_key['ExclusiveStartKey'] = after_key
        while True:
            LOGGER.debug(
                'querying followees: username=%s, from=%s',
                username,
                exclusive_start_key,
            )
            try:
                res = self._table.query(
                    KeyConditionExpression=key_condition,
                    Limit=items_per_query,
                    **exclusive_start_key,
                )
                followee_ids = [item['followeeId'] for item in res['Items']]
                if before is not None:
                    followee_ids.sort()
                for followee_id in followee_ids:
                    yield followee_id
                last_evaluated_key = res.get('LastEvaluatedKey')
                LOGGER.debug('LastEvaluatedKey: %s', last_evaluated_key)
                if not last_evaluated_key:
                    break # items have been exhausted
                exclusive_start_key['ExclusiveStartKey'] = last_evaluated_key
            except self.ProvisionedThroughputExceededException as exc:
                raise TooManyAccessError(
                    'exceeded provisioned DynamoDB table throughput',
                ) from exc
            except self.RequestLimitExceeded as exc:
                raise TooManyAccessError('exceeded API access limit') from exc

    def get_user_follower_count(self, username: str) -> int:
        """Returns the number of followers of a given user.

        :raises TooManyAccessError: if access to the DynamoDB table exceeds
        the limit.
        """
        key_condition = Key('pk').eq(
            UserTable.make_follower_partition_key(username),
        )
        LOGGER.debug('counting followers: %s', username)
        try:
            res = self._table.query(
                KeyConditionExpression=key_condition,
                Select='COUNT',
            )
            return res['Count']
        except self.ProvisionedThroughputExceededException as exc:
            raise TooManyAccessError(
                'exceeded provisioned table throughput',
            ) from exc
        except self.RequestLimitExceeded as exc:
            raise TooManyAccessError('exceeded API access limit') from exc

    def update_last_user_activity(self, username: str):
        """Updates the timestamp of the last activity of a given user.

        :raises NotFoundError: if the user is not ins the user table.

        :raises TooManyAccessError: if access to the DynamoDB table exceeds
        the limit.
        """
        updated_at = current_yyyymmdd_hhmmss_ssssss()
        key = UserTable.make_user_key(username)
        try:
            res = self._table.update_item(
                Key=key,
                UpdateExpression='SET #updatedAt = :updatedAt',
                ExpressionAttributeNames={
                    '#updatedAt': 'updatedAt',
                },
                ExpressionAttributeValues={
                    ':updatedAt': updated_at,
                },
                ConditionExpression=Attr('pk').exists(),
            )
            LOGGER.debug('succeeded to update last activity: %s', res)
        except self.ConditionalCheckFailedException as exc:
            raise NotFoundError(
                f'no such user in the user table: {username}',
            ) from exc
        except self.ProvisionedThroughputExceededException as exc:
            raise TooManyAccessError(
                'exceeded provisioned table throughput',
            ) from exc
        except self.RequestLimitExceeded as exc:
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
    def make_follower_partition_key(username: str) -> str:
        """Returns the partition key of followers of a given user.
        """
        return f'{UserTable.FOLLOWER_PK_PREFIX}{username}'

    @staticmethod
    def make_follower_key(username: str, follower_id: str) -> Dict[str, Any]:
        """Returns a primary key to get a follower from the user table.
        """
        return {
            'pk': UserTable.make_follower_partition_key(username),
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


def make_followee_key(username: str, followee_id: str):
    """Creates the partition key to identify a specified account followed by
    a given user in the user table.
    """
    return {
        'pk': make_followee_partition_key(username),
        'sk': followee_id,
    }


def make_followee_partition_key(username: str):
    """Creates the partition key for the accounts followed by a given user in
    the user table.
    """
    return f'{UserTable.FOLLOWEE_PK_PREFIX}{username}'
