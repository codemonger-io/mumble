# -*- coding: utf-8 -*-

"""Provides access to the object table.
"""

import datetime
from functools import cached_property
import logging
import re
from typing import Any, Dict, Generator, Iterable, Optional, Tuple, TypedDict
from boto3.dynamodb.conditions import Attr, Key
from dateutil.relativedelta import relativedelta
from libactivitypub.activity import Activity
from .exceptions import TooManyAccessError
from .id_scheme import parse_user_activity_id
from .objects_store import load_activity, make_user_outbox_key
from .user_table import User
from .utils import parse_yyyymmdd_hhmmss, parse_yyyymmdd_hhmmss_ssssss


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
    def __init__(self, table):
        """Wraps a boto3's DynamoDB Table resource.

        :param boto3.resource('dynamodb').Table table: object table to be
        wrapped.
        """
        self._table = table

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
                yield ActivityMetadata.parse_item(item)
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
        return self._table.meta.client.excetions

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


class ActivityMetadata:
    """Metadta of an activity.
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
    is_public: bool

    def __init__(
        self,
        pk: str, # pylint: disable=invalid-name
        sk: str, # pylint: disable=invalid-name
        id: str, # pylint: disable=invalid-name, redefined-builtin
        type: str, # pylint: disable=redefined-builtin
        username: str,
        category: str,
        published: datetime.datetime,
        created_at: datetime.datetime,
        updated_at: datetime.datetime,
        is_public: bool,
        table: Optional[ObjectTable]=None,
    ):
        """Initializes with properties.
        """
        self.pk = pk # pylint: disable=invalid-name
        self.sk = sk # pylint: disable=invalid-name
        self.id = id # pylint: disable=invalid-name
        self.type = type
        self.username = username
        self.category = category
        self.published = published
        self.created_at = created_at
        self.updated_at = updated_at
        self.is_public = is_public
        self._table = table

    @staticmethod
    def parse_item(
        item: Dict[str, Any],
        table: Optional[ObjectTable]=None,
    ) -> 'ActivityMetadata':
        """Parses a given item in a DynamoDB table.

        ``item`` must be a ``dict`` similar to the following (other keys may
        be included but are ignored):

        .. code-block:: python

            {
                'pk': 'activity:<username>:<yyyy-mm>',
                'sk': '<ddTHH:MM:ss.SSSSSS>:<unique-part>',
                'id': '<object-id>',
                'type': '<activity-type>',
                'username': '<username>',
                'category': '<category>',
                'published': '<yyyy-mm-ddTHH:MM:ssZ>',
                'createdAt': '<yyyy-mm-ddTHH:MM:ss.SSSSSSZ>',
                'updatedAt': '<yyyy-mm-ddTHH:MM:ss.SSSSSSZ>',
                'isPublic': True
            }

        :raises KeyError: if ``item`` lacks mandatory properties.

        :raises ValueError: if ``item`` is invalid.

        :raises TypeError: if ``item`` is invalid.
        """
        return ActivityMetadata(
            pk=item['pk'],
            sk=item['sk'],
            id=item['id'],
            type=item['type'],
            username=item['username'],
            category=item['category'],
            published=parse_yyyymmdd_hhmmss(item['published']),
            created_at=parse_yyyymmdd_hhmmss_ssssss(item['createdAt']),
            updated_at=parse_yyyymmdd_hhmmss_ssssss(item['updatedAt']),
            is_public=bool(item['isPublic']),
            table=table,
        )

    @cached_property
    def unique_part(self) -> str:
        """Unique part of the activity ID.
        """
        _, _, unique_part = parse_user_activity_id(self.id)
        return unique_part

    @property
    def primary_key(self) -> PrimaryKey:
        """Returns the primary key in the object table to identify this
        activity.
        """
        return {
            'pk': self.pk,
            'sk': self.sk,
        }

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


def format_yyyymm(month: datetime.date) -> str:
    """Converts a given date into the "yyyy-mm" representation.
    """
    return month.strftime('%Y-%m')


def parse_yyyymm(month: str) -> datetime.date:
    """Parses a given string in the "yyyy-mm" form.

    :raises ValueError: if ``month`` is malformed.
    """
    return datetime.datetime.strptime(month, '%Y-%m').date()
