# -*- coding: utf-8 -*-

"""Provides access to the object table.
"""

import datetime
from functools import cached_property
import logging
from typing import Any, Dict, Generator, Optional
from boto3.dynamodb.conditions import Attr, Key
from dateutil.relativedelta import relativedelta
from libactivitypub.activity import Activity
from .exceptions import TooManyAccessError
from .id_scheme import parse_user_activity_id
from .objects_store import load_activity, make_user_outbox_key
from .user_table import User
from .utils import (
    format_yyyymmdd_hhmmss_ssssss,
    parse_yyyymmdd_hhmmss,
    parse_yyyymmdd_hhmmss_ssssss,
    urlencode,
)


LOGGER = logging.getLogger('libmumble.object_table')
LOGGER.setLevel(logging.DEBUG)


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
    ) -> Generator['ActivityMetadata', None, None]:
        """Enumerates activities of a given user.

        Enumerates only public activities.

        Assumes that activities of the user happened between the user's
        creation date and the last active date.

        :param int items_per_query: maximum number of activities fetched in
        a single DynamoDB table query. NOT the total number of activities to
        be enumerated.

        :returns: generator of metadata of activities. activities are sorted
        reverse-chronologically.
        """
        earliest_month = user.created_at.date().replace(day=1)
        query_month = user.last_activity_at.date().replace(day=1)
        LOGGER.debug(
            'query range: earliest=%s, latest=%s',
            earliest_month,
            query_month,
        )
        while query_month >= earliest_month:
            LOGGER.debug('querying activities in %s', query_month)
            activities = self.enumerate_monthly_user_activities(
                user,
                query_month,
                items_per_query,
            )
            for activity in activities:
                yield activity
            query_month -= relativedelta(months=1)

    def enumerate_monthly_user_activities(
        self,
        user: User,
        month: datetime.date,
        items_per_query: int,
    ) -> Generator['ActivityMetadata', None, None]:
        """Enumerates activities of a given user in a specified month.

        Enumerates only public activities.

        :param int items_per_query: maximum number of activities fetched in
        a single DynamoDB table query. NOT the total number of activities to
        be enumerated.

        :returns: generator of metadata of activities. activities are sorted
        reverse-chronologically.

        :raise TooManyAccessError: if DynamoDB requests exceed the limit.
        """
        # loops until items in the month exhaust
        key_condition = Key('pk').eq(
            ObjectTable.make_monthly_user_activity_partition_key(user, month),
        )
        filter_expression = Attr('isPublic').eq(True)
        exclusive_start_key = {
            'ScanIndexForward': False,
        }
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
        user: User,
        month: datetime.date,
    ) -> str:
        """Creates the partition key of given user's activities in a specified
        month.
        """
        return f'activity:{user.username}:{format_yyyymm(month)}'

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

    def encode_key(self) -> str:
        """Encodes the primary key to identify this activity in the object
        table.
        """
        timestamp = format_yyyymmdd_hhmmss_ssssss(self.created_at)
        return urlencode(f'{self.username}:{timestamp}:{self.unique_part}')

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


def format_yyyymm(month: datetime.date) -> str:
    """Converts a given date into the "yyyy-mm" representation.
    """
    return month.strftime('%Y-%m')
