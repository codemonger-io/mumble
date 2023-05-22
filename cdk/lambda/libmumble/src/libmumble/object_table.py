# -*- coding: utf-8 -*-

"""Provides access to the object table.
"""

from abc import ABC
import datetime
from functools import cached_property
import logging
import re
from typing import Any, Dict, Generator, Iterable, Optional, Tuple, TypedDict
from boto3.dynamodb.conditions import Attr, Key
from dateutil.relativedelta import relativedelta
from libactivitypub.activity import Activity
from libactivitypub.data_objects import Note
from libactivitypub.objects import APObject, Reference
from .exceptions import DuplicateItemError, TooManyAccessError
from .id_scheme import parse_user_activity_id, parse_user_post_id
from .objects_store import (
    load_activity,
    load_object,
    make_user_outbox_key,
    make_user_post_object_key,
)
from .user_table import User
from .utils import (
    current_yyyymmdd_hhmmss_ssssss,
    format_yyyymmdd_hhmmss,
    format_yyyymmdd_hhmmss_ssssss,
    parse_yyyymmdd_hhmmss,
    parse_yyyymmdd_hhmmss_ssssss,
)


LOGGER = logging.getLogger('libmumble.object_table')
LOGGER.setLevel(logging.DEBUG)


class PrimaryKey(TypedDict):
    """Primary key of the object table.
    """
    pk: str
    """Partition key."""
    sk: str
    """Sort key."""


class ObjectTable:
    """Provides access to the object table.

    The object table manages metadata and history of objects.
    """
    REPLY_SK_PREFIX = 'reply:'

    def __init__(self, table):
        """Wraps a boto3's DynamoDB Table resource.

        :param boto3.resource('dynamodb').Table table: object table to be
        wrapped.
        """
        self._table = table

    def put_activity(self, activity: Activity):
        """Puts a given activity into the object table.

        :raises ValueError: if ``activity.id`` is invalid.

        :raises DuplicateItemError: if the activity is already in the object
        table.

        :raises TooManyAccessError: if access to the DynamoDB table exceeds
        the limit.
        """
        _, username, unique_part = parse_user_activity_id(activity.id)
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        created_at = format_yyyymmdd_hhmmss_ssssss(now)
        updated_at = created_at
        if hasattr(activity, 'published'):
            published = activity.published
        else:
            published = format_yyyymmdd_hhmmss(now)
        key = make_activity_key(username, unique_part, now)
        try:
            res = self._table.put_item(
                Item={
                    **key,
                    'id': activity.id,
                    'type': activity.type,
                    'username': username,
                    'category': 'activity',
                    'published': published,
                    'createdAt': created_at,
                    'updatedAt': updated_at,
                    'isPublic': activity.is_public(),
                },
                ConditionExpression=Attr('pk').not_exists(),
            )
            LOGGER.debug('succeeded to put activity: %s', res)
        except self.ConditionalCheckFailedException as exc:
            raise DuplicateItemError(
                'activity already exists. use `activate_post` instead'
            ) from exc
        except self.ProvisionedThroughputExceededException as exc:
            raise TooManyAccessError(
                'provisioned DynamoDB table throughput exceeded',
            ) from exc
        except self.RequestLimitExceeded as exc:
            raise TooManyAccessError('too many API requests') from exc

    def enumerate_user_activities(
        self,
        user: User,
        items_per_query: int,
        before: Optional[PrimaryKey]=None,
        after: Optional[PrimaryKey]=None,
    ) -> Generator['ActivityMetadata', None, None]:
        """Enumerates activities of a given user.

        Enumerates only public activities.

        Assumes that activities of the user happened between the user's
        creation date and the last active date.

        Returns the latest activities if none of ``before`` and ``after`` is
        specified.

        :param int items_per_query: maximum number of activities fetched in
        a single DynamoDB table query. NOT the total number of activities to
        be enumerated.

        :param Optional[PrimaryKey] before: queries activities before this
        key.

        :param Optional[PrimaryKey] after: queries activities after this key.

        :returns: generator of metadata of activities. activities are
        chronologically ordered if ``after`` is specified, otherwise
        reverse-chronologically ordered.

        :raises ValueError: if both of ``before`` and ``after`` are specified,
        or if ``before`` does not represent an activity key,
        or if ``after`` does not represent an activity key,
        or if the user in ``before`` does not match ``user``,
        or if the user in ``after`` does not match ``user``.
        """
        if before is not None and after is not None:
            raise ValueError('both of before and after are specified')
        earliest_month = user.created_at.date().replace(day=1)
        latest_month = user.last_activity_at.date().replace(day=1)
        LOGGER.debug(
            'query range: earliest=%s, latest=%s',
            earliest_month,
            latest_month,
        )
        def reverse_chrono_iterator(
            month: datetime.date,
        ) -> Generator[datetime.date, None, None]:
            while month >= earliest_month:
                yield month
                month -= relativedelta(months=1)
        def chrono_iterator(
            month: datetime.date,
        ) -> Generator[datetime.date, None, None]:
            while month <= latest_month:
                yield month
                month += relativedelta(months=1)
        month_iterator: Iterable[datetime.date]
        chronological = False
        if before is not None:
            LOGGER.debug('querying activities before %s', before)
            username, before_month = parse_activity_partition_key(before['pk'])
            if user.username != username:
                raise ValueError(
                    'before key is for different user:'
                    f' {user.username} vs {username}',
                )
            month_iterator = reverse_chrono_iterator(before_month)
        elif after is not None:
            LOGGER.debug('querying activities after %s', after)
            username, after_month = parse_activity_partition_key(after['pk'])
            if user.username != username:
                raise ValueError(
                    'after key is for different user:'
                    f' {user.username} vs {username}',
                )
            month_iterator = chrono_iterator(after_month)
            chronological = True # keeps subsequent queries chronological
        else:
            LOGGER.debug('querying latest activities')
            month_iterator = reverse_chrono_iterator(latest_month)
        for query_month in month_iterator:
            LOGGER.debug('querying activities in %s', query_month)
            activities = self.enumerate_monthly_user_activities(
                user,
                query_month,
                items_per_query,
                before=before,
                after=after,
                chronological=chronological,
            )
            for activity in activities:
                yield activity
            # before and after are meaningless in the subsequent queries
            before = None
            after = None

    def enumerate_monthly_user_activities(
        self,
        user: User,
        month: datetime.date,
        items_per_query: int,
        before: Optional[PrimaryKey]=None,
        after: Optional[PrimaryKey]=None,
        chronological: Optional[bool]=False,
    ) -> Generator['ActivityMetadata', None, None]:
        """Enumerates activities of a given user in a specified month.

        Enumerates only public activities.

        Returns the latest activities in the month if none of ``before`` and
        ``after`` is specified.

        :param int items_per_query: maximum number of activities fetched in
        a single DynamoDB table query. NOT the total number of activities to
        be enumerated.

        :param Optional[PrimaryKey] before: queries activities before this
        key.

        :param Optional[PrimaryKey] after: queries activities after this key.

        :param Optional[bool] chronological: whether activities are
        chronologically ordered. ignored if either of ``before`` and ``after``
        is specified.

        :returns: generator of metadata of activities. activities are
        chronologically ordered if ``after`` is specified, or ``chronological``
        is ``True`` without ``before``, otherwise reverse-chronologically
        ordered.

        :raise TooManyAccessError: if DynamoDB requests exceed the limit.

        :raises ValueError: if both of ``before`` and ``after`` are specified.
        """
        if before is not None and after is not None:
            raise ValueError('both of before and after are specified')
        # loops until items in the month exhaust
        key_condition = Key('pk').eq(
            ObjectTable.make_monthly_user_activity_partition_key(
                user.username,
                month,
            ),
        )
        filter_expression = Attr('isPublic').eq(True)
        exclusive_start_key: Dict[str, Any] = {
            'ScanIndexForward': chronological,
        }
        if before is not None:
            exclusive_start_key['ExclusiveStartKey'] = before
            exclusive_start_key['ScanIndexForward'] = False
                # forces reverse-chronological
        if after is not None:
            exclusive_start_key['ExclusiveStartKey'] = after
            exclusive_start_key['ScanIndexForward'] = True
                # forces chronological
        while True:
            LOGGER.debug('querying activities: %s', exclusive_start_key)
            try:
                res = self._table.query(
                    KeyConditionExpression=key_condition,
                    FilterExpression=filter_expression,
                    Limit=items_per_query,
                    **exclusive_start_key,
                )
            except self.ProvisionedThroughputExceededException as exc:
                raise TooManyAccessError(
                    'provisioned throughput exceeded',
                ) from exc
            except self.RequestLimitExceeded as exc:
                raise TooManyAccessError('too many requests') from exc
            items = res['Items']
            for item in items:
                yield ActivityMetadata(item, table=self)
            last_evaluated_key = res.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break # all the items were exhausted
            exclusive_start_key['ExclusiveStartKey'] = last_evaluated_key

    def put_post(self, post: Note):
        """Puts a given post (note) into the object table.

        :raises DuplicateItemError: if ``post`` is already in the object table.

        :raises TooManyAccessError: if access to the DynamoDB table exceeds
        the limit.
        """
        _, username, unique_part = parse_user_post_id(post.id)
        key = make_user_post_key(username, unique_part)
        created_at = current_yyyymmdd_hhmmss_ssssss()
        updated_at = created_at
        try:
            res = self._table.put_item(
                Item={
                    **key,
                    'id': post.id,
                    'type': post.type,
                    'username': username,
                    'category': 'post',
                    'published': post.published,
                    'createdAt': created_at,
                    'updatedAt': updated_at,
                    'isPublic': post.is_public(),
                    'replyCount': 0,
                },
                ConditionExpression=Attr('pk').not_exists(),
            )
            LOGGER.debug('succeeded to put post: %s', res)
        except self.ConditionalCheckFailedException as exc:
            raise DuplicateItemError(
                'post already exists. use `update_post` instead',
            ) from exc
        except self.ProvisionedThroughputExceededException as exc:
            raise TooManyAccessError(
                'provisioned DynamoDB table throughput exceeded',
            ) from exc
        except self.RequestLimitExceeded as exc:
            raise TooManyAccessError('too many requests') from exc

    def find_user_post(
        self,
        username: str,
        unique_part: str,
    ) -> Optional['PostMetadata']:
        """Finds a specified post of a given user.

        :returns: ``None`` if the specified post does not exist.

        :raises TooManyAccessError: if the DynamoDB access exceeds the limit.
        """
        try:
            res = self._table.get_item(
                Key=make_user_post_key(username, unique_part),
            )
            item = res.get('Item')
            if item is None:
                return None
            return PostMetadata(item, table=self)
        except self.ProvisionedThroughputExceededException as exc:
            raise TooManyAccessError(
                'exceeded provisioned DynamoDB table throughput',
            ) from exc
        except self.RequestLimitExceeded as exc:
            raise TooManyAccessError('too many API requests') from exc

    def add_reply_to_post(self, username: str, unique_part: str, obj: APObject):
        """Adds a given object as a reply to a specified post.

        Does not check if the original post exists.

        :raises DuplicateItemError: if the specified reply already exists in
        the object table.

        :raises TooManyAccessError: if access to the DynamoDB table exceeds
        the limit.
        """
        key = make_user_post_reply_key(username, unique_part, obj)
        try:
            res = self._table.put_item(
                Item={
                    **key,
                    'id': obj.id,
                    'category': 'reply',
                    'published': obj.published,
                    'isPublic': obj.is_public(),
                },
                ConditionExpression=Attr('pk').not_exists(),
            )
            LOGGER.debug('succeeded to add a reply: %s', res)
        except self.ConditionalCheckFailedException as exc:
            raise DuplicateItemError('duplicate reply') from exc
        except self.ProvisionedThroughputExceededException as exc:
            raise TooManyAccessError(
                'exceeded provisioned DynamoDB table throughput',
            ) from exc
        except self.RequestLimitExceeded as exc:
            raise TooManyAccessError('too many API requests') from exc

    def enumerate_replies_to_post(
        self,
        username: str,
        unique_part: str,
        items_per_query: int,
        before: Optional[PrimaryKey]=None,
        after: Optional[PrimaryKey]=None,
    ) -> Generator['ReplyMetadata', None, None]:
        """Enumerates replies to a specified post.

        Enumerates only public replies.

        :param int items_per_query: maximum number of items fetched in a
        single DynamoDB query. NOT the total number of replies to pull.

        :param Optional[PrimaryKey] before: queries replies before this key.

        :param Optional[PrimaryKey] after: queries replies after this key.

        :returns: generator of replies to the post. reverse-chronologically
        ordered.

        :raises ValueError: if both of ``before`` and ``after`` are specified.

        :raises TooManyAccessError: if access to the DynamoDB table exceeds
        the limit.
        """
        if before is not None and after is not None:
            raise ValueError('both of before and after are specified')
        key_condition = Key('pk').eq(
            make_user_post_partition_key(username, unique_part),
        ) & Key('sk').begins_with(ObjectTable.REPLY_SK_PREFIX)
        filter_expression = Attr('isPublic').eq(True)
        exclusive_start_key: Dict[str, Any] = {
            'ScanIndexForward': False,
        }
        if before is not None:
            exclusive_start_key['ExclusiveStartKey'] = before
        if after is not None:
            exclusive_start_key['ExclusiveStartKey'] = after
            exclusive_start_key['ScanIndexForward'] = True
        while True:
            LOGGER.debug('querying replies: from=%s', exclusive_start_key)
            try:
                res = self._table.query(
                    KeyConditionExpression=key_condition,
                    FilterExpression=filter_expression,
                    Limit=items_per_query,
                    **exclusive_start_key,
                )
            except self.ProvisionedThroughputExceededException as exc:
                raise TooManyAccessError(
                    'exceeded provisioned DynamoDB table throughput',
                ) from exc
            except self.RequestLimitExceeded as exc:
                raise TooManyAccessError('too many API requests') from exc
            items = res['Items']
            if after is not None:
                items.reverse() # chronological → reverse-chronological
            for item in items:
                yield ReplyMetadata(item, table=self)
            last_evaluated_key = res.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break # all the items were exhausted
            exclusive_start_key['ExclusiveStartKey'] = last_evaluated_key

    @staticmethod
    def make_monthly_user_activity_partition_key(
        username: str,
        month: datetime.date,
    ) -> str:
        """Creates the partition key of given user's activities in a specified
        month.
        """
        return f'activity:{username}:{format_yyyymm(month)}'

    @staticmethod
    def make_oldest_user_activity_key(user: User) -> PrimaryKey:
        """Creates the primary key to query the oldest activity of a given
        user.
        """
        earliest_month = user.created_at.date().replace(day=1)
        return {
            'pk': ObjectTable.make_monthly_user_activity_partition_key(
                user.username,
                earliest_month,
            ),
            'sk': '00T00:00:00.000000:@',
        }

    @property
    def exceptions(self):
        """boto3 exceptions.
        """
        return self._table.meta.client.exceptions

    @property
    def ConditionalCheckFailedException(self): # pylint: disable=invalid-name
        """boto3's ConditionalCheckFailedException.
        """
        return self.exceptions.ConditionalCheckFailedException

    @property
    def ProvisionedThroughputExceededException(self): # pylint: disable=invalid-name
        """boto3's ProvisionedThroughputExceededException.
        """
        return self.exceptions.ProvisionedThroughputExceededException

    @property
    def RequestLimitExceeded(self): # pylint: disable=invalid-name
        """boto3's RequestLimitExceeded.
        """
        return self.exceptions.RequestLimitExceeded


class ObjectMetadata(ABC):
    """Base class for metadata of an object.
    """
    pk: str
    sk: str
    id: str
    type: str
    username: str
    category: str
    published: datetime.datetime
    created_at: datetime.datetime
    updated_at: datetime.datetime

    def __init__(
        self,
        item: Dict[str, Any],
        table: Optional[ObjectTable]=None,
    ):
        """Initializes by parsing a given item in the DynamoDB table for
        objects.

        ``item`` must be a ``dict`` similar to the following:

        .. code-block:: python

            {
                'pk': '<partition-key>',
                'sk': '<sort-key>',
                'type': '<object-type>',
                'username': '<username>',
                'category': '<category>',
                'published': '<yyyy-mm-ddTHH:MM:ssZ>',
                'createdAt': '<yyyy-mm-ddTHH:MM:ss.SSSSSSZ>',
                'updatedAt': '<yyyy-mm-ddTHH:MM:ss.SSSSSSZ>',
                'isPublic': True
            }

        :param Optional[ObjectTable] table: optional table that manages the
        item.

        :raises KeyError: if ``item`` lacks any mandatory property.

        :raises ValueError: if ``item`` is invalid.
        """
        self.pk = item['pk'] # pylint: disable=invalid-name
        self.sk = item['sk'] # pylint: disable=invalid-name
        self.id = item['id'] # pylint: disable=invalid-name
        self.type = item['type']
        self.username = item['username']
        self.category = item['category']
        self.published = parse_yyyymmdd_hhmmss(item['published'])
        self.created_at = parse_yyyymmdd_hhmmss_ssssss(item['createdAt'])
        self.updated_at = parse_yyyymmdd_hhmmss_ssssss(item['updatedAt'])
        self.is_public = bool(item['isPublic'])
        self._table = table

    @property
    def primary_key(self) -> PrimaryKey:
        """Primary key of the object.
        """
        return {
            'pk': self.pk,
            'sk': self.sk,
        }


class ActivityMetadata(ObjectMetadata):
    """Metadta of an activity.
    """
    @cached_property
    def unique_part(self) -> str:
        """Unique part of the activity ID.

        :raises ValueError: if the activity ID is invalid.
        """
        _, _, unique_part = parse_user_activity_id(self.id)
        return unique_part

    def resolve(self, s3_client, objects_bucket_name: str) -> Activity:
        """Resolves the activity object.

        :param boto3.client('s3') s3_client: S3 client that access the S3
        bucket for objects.

        :param str objects_bucket_name: name of the S3 bucket that stores
        objects.

        :raises NotFoundError: if the activity object is not found.

        :raises ValueError: if the loaded object is invalid.

        :raises TypeError: if the loaded object is invalid.
        """
        return load_activity(s3_client, {
            'bucket': objects_bucket_name,
            'key': make_user_outbox_key(self.username, self.unique_part),
        })


class PostMetadata(ObjectMetadata):
    """Metadata of a post object.
    """
    reply_count: int
    """Number of replies to the post."""

    def __init__(
        self,
        item: Dict[str, Any],
        table: Optional[ObjectTable]=None,
    ):
        """Initializes with a DynamoDB table item representing a post.

        ``item`` must have the following key in addition to those required by
        ``ObjectMetadata``.

        .. code-block:: python

            {
                'replyCount': 123
            }

        :raises KeyError: if ``item`` lacks ``replyCount``,
        or if ``item`` lacks other mandatory keys required by
        ``ObjectMetadata``.

        :raises ValueError: if ``replyCount`` is not a number,
        or``ObjectMetadata`` may raise.
        """
        super().__init__(item, table=table)
        self.reply_count = int(item['replyCount'])

    @cached_property
    def unique_part(self) -> str:
        """Unique part of the post ID.

        :raises ValueError: if the post ID is invalid.
        """
        _, _, unique_part = parse_user_post_id(self.id)
        return unique_part

    @property
    def replies_id(self) -> str:
        """ID (URI) of the replies to the post.
        """
        return f'{self.id}/replies'

    def add_reply(self, reply: APObject):
        """Adds a reply to this post.

        :raises AttributeError: if no user table is associated with this post.
        """
        if self._table is None:
            raise AttributeError('user table is not associated')
        self._table.add_reply_to_post(self.username, self.unique_part, reply)

    def enumerate_replies(
        self,
        items_per_query: int,
        before: Optional[str]=None,
        after: Optional[str]=None,
    ) -> Generator['ReplyMetadata', None, None]:
        """Enumerates replies to the post.

        ``before`` and ``after`` must be serialized with
        :py:func:`serialize_user_post_reply_key`.

        :param int items_per_query: maximum number of items to be fetched in
        a single DynamoDB query. NOT the total number of replies to pull.

        :param Optional[str] before: obtains replies before this serialized
        key.

        :param Optional[str] after: obtains replies after this serialized key.

        :returns: generator of metadata of replies. reverse-chronologically
        oredered.

        :raises AttributeError: if no user table is associated with this post.

        :raises ValueError: if both of ``before`` and ``after`` are specified,
        or if ``before`` is not a valid key,
        or if ``after`` is not a valid key.
        """
        if self._table is None:
            raise AttributeError('user table is not associated')
        before_key: Optional[PrimaryKey] = None
        if before is not None:
            before_key = deserialize_user_post_reply_key(
                self.username,
                self.unique_part,
                before,
            )
        after_key: Optional[PrimaryKey] = None
        if after is not None:
            after_key = deserialize_user_post_reply_key(
                self.username,
                self.unique_part,
                after,
            )
        return self._table.enumerate_replies_to_post(
            self.username,
            self.unique_part,
            items_per_query,
            before=before_key,
            after=after_key,
        )

    def resolve(self, s3_client, objects_bucket_name: str) -> Note:
        """Resolves the post object.

        :param boto3.client('s3') s3_client: S3 client that access the S3
        bucket for objects.

        :param str objects_bucket_name: name of the S3 bucket that stores
        objects.

        :raises NotFoundError: if the post object is not found.

        :raises ValueError: if the loaded object is invalid.

        :raises TypeError: if the loaded object is invalid.
        """
        obj = load_object(s3_client, {
            'bucket': objects_bucket_name,
            'key': make_user_post_object_key(self.username, self.unique_part),
        }).cast(Note)
        obj.replies = Reference(self.make_reply_collection())
        return obj

    def make_reply_collection(self) -> Dict[str, Any]:
        """Retuns a collection of replies to the post.

        :returns: ``dict`` representing an ``OrderedCollection`` of replies
        to the post.
        """
        replies_id = self.replies_id
        return {
            'id': replies_id,
            'type': 'OrderedCollection',
            'totalItems': self.reply_count,
            'first': f'{replies_id}?page=true',
        }


class ReplyMetadata:
    """Metadata of a reply.
    """
    OLDEST_SERIALIZED_KEY = '1970-01-01T00:00:00Z:!'
    """Oldest serialized key."""

    pk: str
    """Partition key in the DynamoDB table."""
    sk: str
    """Sort key in the DynamoDB table."""
    id: str
    """ID of the reply object."""
    published: str
    """Published date time."""
    is_public: bool
    """Whether the post is public."""

    def __init__(self, item: Dict[str, Any], table: Optional[ObjectTable]=None):
        """Initializes from an item in the DynamoDB table.

        ``item`` must be a ``dict`` similar to the following:

        .. code-block:: python

            {
                'pk': 'object:<username>:<category>:<unique-part>',
                'sk': 'reply:<yyyy-mm-ddTHH:MM:ssZ>:<reply-object-id>',
                'id': '<reply-object-id>',
                'category': 'reply',
                'published': '<yyyy-mm-ddTHH:MM:ssZ>',
                'isPublic': True
            }

        :raises KeyError: if ``item`` lacks any mandatory key.
        """
        self.pk = item['pk'] # pylint: disable=invalid-name
        self.sk = item['sk'] # pylint: disable=invalid-name
        self.id = item['id'] # pylint: disable=invalid-name
        self.published = item['published']
        self.is_public = item['isPublic']
        self._table = table

    @cached_property
    def serialized_key(self) -> str:
        """Serialized form of the key to identify the reply.

        You can deserialize the result with
        :py:func:`deserialize_user_post_reply_key`.
        """
        return serialize_user_post_reply_key({
            'pk': self.pk,
            'sk': self.sk,
        })


def make_activity_key(
    username: str,
    unique_part: str,
    created_at: datetime.datetime,
) -> PrimaryKey:
    """Creates the primary key for an activity in the object table.

    Returns a ``dict`` similar to the following:

    .. code-block:: python

        {
            'pk': 'activity:<username>:<yyyy-mm>',
            'sk': '<ddTHH:MM:ss.SSSSSS>:<unique-part>'
        }
    """
    year_month = format_yyyymm(created_at.date())
    date_time = format_dd_hhmmss_ssssss(created_at)
    return {
        'pk': f'activity:{username}:{year_month}',
        'sk': f'{date_time}:{unique_part}',
    }


def parse_activity_partition_key(
    pk: str, # pylint: disable=invalid-name
) -> Tuple[str, datetime.date]:
    """Parses a given partition key of an activity.

    :param str pk: in the form "activity:<username>:<year-month>".

    :returns: tuple of the username and month.

    :raises ValueError: if ``pk`` does not represent an activity partition key.
    """
    match = re.match(r'activity:([^:]+):([0-9]{4}-[0-9]{2})', pk)
    if match is None:
        raise ValueError(f'invalid activity partition key: {pk}')
    username = match[1]
    year_month = parse_yyyymm(match[2])
    return username, year_month


def serialize_activity_key(key: PrimaryKey) -> str:
    """Serializes a given primary key identifying an activity.

    ``key`` must be a ``dict`` similar to the following:

    .. code-block:: python

        {
            'pk': 'activity:<username>:<yyyy-mm>',
            'sk': '<ddTHH:MM:ss.SSSSSS>:<unique-part>'
        }

    :returns: "<yyyy-mm-ddTHH:MM:ss.SSSSSS>:<unique-part>".
    You have to supply the username when you deserialize it.

    :raises ValueError: if ``key`` does not represent an activity key.
    """
    pk_match = re.match(r'^activity:[^:]+:([0-9]{4}-[0-9]{2})$', key['pk'])
    if pk_match is None:
        raise ValueError(f'invalid activity key (pk): {key}')
    sk_match = re.match(
        r'^([0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}):([^:]+)$',
        key['sk'],
    )
    if sk_match is None:
        raise ValueError(f'invalid activity key (sk): {key}')
    year_month = pk_match[1]
    date_time = sk_match[1]
    unique_part = sk_match[2]
    return f'{year_month}-{date_time}:{unique_part}'


def deserialize_activity_key(key: str, username: str) -> PrimaryKey:
    """Deserializes a given serialized key identifying an activity.

    ``key`` must be in the form "<yyyy-mm-ddTHH:MM:ss.SSSSSS>:<unique-part>".

    Returns a ``dict`` similar to the following:

    .. code-block:: python

        {
            'pk': 'activity:<username>:<yyyy-mm>',
            'sk': '<ddTHH:MM:ss.SSSSSS>:<unique-part>'
        }

    :raises ValueError: if ``key`` does not represent a serialized activity
    key.
    """
    match = re.match(
        r'^([0-9]{4}-[0-9]{2})'
        r'-([0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6})'
        r':([^:]+)$',
        key,
    )
    if match is None:
        raise ValueError(f'invalid serialized activity key: {key}')
    year_month = match[1]
    date_time = match[2]
    unique_part = match[3]
    return {
        'pk': f'activity:{username}:{year_month}',
        'sk': f'{date_time}:{unique_part}',
    }


def make_user_post_key(username: str, unique_part: str) -> PrimaryKey:
    """Creates the primary key to identify a specified post object of a given
    user in the object table.
    """
    return {
        'pk': make_user_post_partition_key(username, unique_part),
        'sk': 'metadata',
    }


def make_user_post_partition_key(username: str, unique_part: str) -> str:
    """Creates the partition key to look up a specified post object of a given
    user in the object table.
    """
    return f'object:{username}:post:{unique_part}'


def make_user_post_reply_key(
    username: str,
    unique_part: str,
    obj: APObject,
) -> PrimaryKey:
    """Creates the primary key to identify a specified reply to user's post.
    """
    return {
        'pk': make_user_post_partition_key(username, unique_part),
        'sk': f'{ObjectTable.REPLY_SK_PREFIX}{obj.published}:{obj.id}',
    }


def serialize_user_post_reply_key(key: PrimaryKey) -> str:
    """Serializes a given primary key identifying a reply to a post.

    Given ``key`` similar to the following:

    .. code-block:: python

        {
            'pk': 'object:<username>:<category>:<unique-part>',
            'sk': 'reply:<yyyy-mm-ddTHH:MM:ssZ>:<reply-object-id>'
        }

    returns "<yyyy-mm-ddTHH:MM:ssZ>:<reply-object-id>".

    When you deserialize the result with
    :py:func:`deserialize_user_post_reply_key`, you have to supply the username
    and unique part of the original post.

    You have to properly encode the result if you want to embed it in a URL.

    :raises ValueError: if ``key`` is invalid.
    """
    match = re.match(rf'^{ObjectTable.REPLY_SK_PREFIX}(.+)', key['sk'])
    if match is None:
        raise ValueError(f'invalid reply key (sk): {key["sk"]}')
    return match.group(1)


def deserialize_user_post_reply_key(
    username: str,
    unique_part: str,
    key: str,
) -> PrimaryKey:
    """Deserializes a given serialized key of a reply.

    :param str username: username of the user who owns the original post.

    :param str unique_part: unique part in the ID of the original post.

    :param str key: key serialized with
    :py:func:`serialize_user_post_reply_key`.
    """
    return {
        'pk': make_user_post_partition_key(username, unique_part),
        'sk': f'{ObjectTable.REPLY_SK_PREFIX}{key}',
    }


def format_yyyymm(month: datetime.date) -> str:
    """Converts a given date into the "yyyy-mm" representation.
    """
    return month.strftime('%Y-%m')


def format_dd_hhmmss_ssssss(time: datetime.datetime) -> str:
    """Converts a given datetime into the "ddTHH:MM:ss.SSSSSS" representation.

    The timezone is normalized to UTC.
    No normalization is performed if ``time`` is naive.
    """
    offset = time.utcoffset()
    if offset is not None and offset.total_seconds() != 0:
        time = time.astimezone(datetime.timezone.utc)
    return time.strftime('%dT%H:%M:%S.%f')


def parse_yyyymm(month: str) -> datetime.date:
    """Parses a given string in the "yyyy-mm" form.

    :raises ValueError: if ``month`` is malformed.
    """
    return datetime.datetime.strptime(month, '%Y-%m').date()
