# -*- coding: utf-8 -*-

"""Tests ``libmumble.object_table``.
"""

import datetime
from libmumble.object_table import (
    deserialize_activity_key,
    format_dd_hhmmss_ssssss,
    format_yyyymm,
    parse_activity_partition_key,
    parse_yyyymm,
    serialize_activity_key,
)
import pytest
import pytz


def test_parse_activity_partition_key():
    """Tests ``parse_activity_partition_key`` with a valid key.
    """
    pk = 'activity:kemoto:2023-05'
    expected = ('kemoto', datetime.date(2023, 5, 1))
    assert parse_activity_partition_key(pk) == expected


def test_parse_activity_partition_key_with_non_activity_key():
    """Tests ``parse_activity_partition_key`` with a non-activity key.
    """
    pk = 'object:kemoto:post:00000000-0123'
    with pytest.raises(ValueError):
        parse_activity_partition_key(pk)


def test_parse_activity_partition_key_with_invalid_month():
    """Tests ``parse_activity_partition_key`` with an invalid month.
    """
    pk = 'activity:kemoto:2023-00'
    with pytest.raises(ValueError):
        parse_activity_partition_key(pk)


def test_serialize_activity_key():
    """Tests ``serialize_activity_key`` with a valid key.
    """
    key = {
        'pk': 'activity:kemoto:2023-05',
        'sk': '15T01:04:00.123456:12345678-1234-abcd',
    }
    expected = '2023-05-15T01:04:00.123456:12345678-1234-abcd'
    assert serialize_activity_key(key) == expected


def test_serialize_activity_key_with_invalid_pk():
    """Tests ``serialize_activity_key`` with an invalid "pk".
    """
    key = {
        'pk': 'object:kemoto:post:12345678-1234-abcd',
        'sk': '15T01:04:00.123456:12345678-1234-abcd',
    }
    with pytest.raises(ValueError):
        serialize_activity_key(key)


def test_serialize_activity_key_with_invalid_sk():
    """Tests ``serialize_activity_key`` with an invalid "sk".
    """
    key = {
        'pk': 'activity:kemoto:2023-05',
        'sk': 'reply:2023-05-15T01:12:00.123456Z:abcdefg',
    }
    with pytest.raises(ValueError):
        serialize_activity_key(key)


def test_deserialize_activity_key():
    """Tests ``deserialize_activity_key`` with a valid key.
    """
    key = '2023-05-15T01:04:00.123456:12345678-1234-abcd'
    username = 'kemoto'
    expected = {
        'pk': 'activity:kemoto:2023-05',
        'sk': '15T01:04:00.123456:12345678-1234-abcd',
    }
    assert deserialize_activity_key(key, username) == expected


def test_deserialize_activity_key_with_invalid_key():
    """Tests ``deserialize_activity_key`` with an invalid key.
    """
    key = '01:16:01.123456 on May 15, 2023:12345678-1234-abcd'
    username = 'kemoto'
    with pytest.raises(ValueError):
        deserialize_activity_key(key, username)


def test_format_yyyymm():
    """Tests ``format_yyyymm`` with ``date(2023, 5, 12)``.
    """
    date = datetime.date(2023, 5, 12)
    assert format_yyyymm(date) == '2023-05'


def test_format_dd_hhmmss_ssssss():
    """Tests ``format_dd_hhmmss_ssssss`` with "2023-05-17T08:34:01.012345Z".
    """
    time = datetime.datetime(
        2023, 5, 17, 8, 34, 1, 12345, tzinfo=datetime.timezone.utc,
    )
    expected = '17T08:34:01.012345'
    assert format_dd_hhmmss_ssssss(time) == expected


def test_format_dd_hhmmss_ssssss_in_jst():
    """Tests ``format_dd_hhmmss_ssssss`` with
    "2023-05-17T08:34:01.012345+09:00" (JST).
    """
    jst = pytz.timezone('Asia/Tokyo')
    time = jst.localize(datetime.datetime(2023, 5, 17, 8, 34, 1, 12345))
    expected = '16T23:34:01.012345'
    assert format_dd_hhmmss_ssssss(time) == expected


def test_format_dd_hhmmss_ssssss_with_naive():
    """Tests ``format_dd_hhmmss_ssssss`` with naive
    "2023-05-17T08:34:01.012345".
    """
    time = datetime.datetime(2023, 5, 17, 8, 34, 1, 12345)
    expected = '17T08:34:01.012345'
    assert format_dd_hhmmss_ssssss(time) == expected


def test_parse_yyyymm():
    """Tests ``parse_yyyymm`` with "2023-05".
    """
    month = '2023-05'
    assert parse_yyyymm(month) == datetime.date(2023, 5, 1)


def test_parse_yyyymm_with_invalid_string():
    """Tests ``parse_yyyymm`` with "May 2023".
    """
    month = 'May 2023'
    with pytest.raises(ValueError):
        parse_yyyymm(month)
