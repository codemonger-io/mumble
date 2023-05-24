# -*- coding: utf-8 -*-

"""Tests ``libmumble.utils``.
"""

from datetime import datetime, timezone
from libmumble.utils import (
    chunk,
    format_yyyymmdd_hhmmss,
    format_yyyymmdd_hhmmss_ssssss,
    parse_yyyymmdd_hhmmss,
    parse_yyyymmdd_hhmmss_ssssss,
    to_urlsafe_base64,
    urlencode,
)
import pytest
import pytz


def test_urlencode():
    """Tests ``urlencode``.
    """
    input = 'https://mumble.codemonger.io/users/kemoto'
    expected = 'https%3A%2F%2Fmumble.codemonger.io%2Fusers%2Fkemoto'
    assert urlencode(input) == expected


def test_to_urlsafe_base64():
    """Tests ``to_urlsafe_base64``.
    """
    input = (
        'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        'abcdefghijklmnopqrstuvwxyz'
        '0123456789+/=='
    ) # not a valid Base64 but does not matter
    expected = (
        'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        'abcdefghijklmnopqrstuvwxyz'
        '0123456789-_'
    )
    assert to_urlsafe_base64(input) == expected


def test_to_urlsafe_base64_with_empty_string():
    """Tests ``to_urlsafe_base64`` with an empty string.
    """
    assert to_urlsafe_base64('') == ''


def test_chunk_with_exact_by_3():
    """Tests ``chunk`` with a sequence exactly split into chunks of 3 items.
    """
    sequence = [
        1, 2, 3,
        4, 5, 6,
        7, 8, 9,
    ]
    expected = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
    ]
    assert list(chunk(sequence, 3)) == expected


def test_chunk_with_by_3_remaining_1():
    """Tests ``chunk`` with a sequence remaining 1 item if chunked by 3 items.
    """
    sequence = [
        1, 2, 3,
        4, 5, 6,
        7,
    ]
    expected = [
        [1, 2, 3],
        [4, 5, 6],
        [7],
    ]
    assert list(chunk(sequence, 3)) == expected


def test_chunk_with_by_3_remaining_2():
    """Tests ``chunk`` with a sequence remaining 2 items if chunked by 3 items.
    """
    sequence = [
        1, 2, 3,
        4, 5, 6,
        7, 8,
    ]
    expected = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8],
    ]
    assert list(chunk(sequence, 3)) == expected


def test_chunk_with_empty_sequence():
    """Tests ``chunk`` with an empty sequence.
    """
    assert list(chunk([], 3)) == []


def test_chunk_with_iterator():
    """Tests ``chunk`` with an iterator.
    """
    sequence = iter([
        1, 2, 3,
        4, 5, 6,
        7, 8, 9,
    ])
    expected = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
    ]
    assert list(chunk(sequence, 3)) == expected


def test_format_yyyymmdd_hhmmss_ssssss():
    """Tests ``format_yyyymmdd_hhmmss_ssssss``.
    """
    time = datetime(2023, 4, 24, 17, 2, 23, 123456, tzinfo=timezone.utc)
    assert format_yyyymmdd_hhmmss_ssssss(time) == '2023-04-24T17:02:23.123456Z'


def test_format_yyyymmdd_hhmmss_ssssss_with_jst():
    """Tests ``format_yyyymmdd_hhmmss_ssssss`` with a datetime in JST.
    """
    jst = pytz.timezone('Asia/Tokyo')
    time = jst.localize(datetime(2023, 4, 24, 23, 50, 9, 789))
    assert format_yyyymmdd_hhmmss_ssssss(time) == '2023-04-24T14:50:09.000789Z'


def test_format_yyyymmdd_hhmmss_ssssss_with_naive():
    """Tests ``format_yyyymmdd_hhmmss_ssssss`` with a naive datetime.
    """
    time = datetime(2023, 4, 24, 23, 57, 59, 2099)
    with pytest.raises(ValueError):
        format_yyyymmdd_hhmmss_ssssss(time)


def test_format_yyyymmdd_hhmmss():
    """Tests ``format_yyyymmdd_hhmmss``.
    """
    time = datetime(2023, 4, 27, 17, 57, 10, tzinfo=timezone.utc)
    assert format_yyyymmdd_hhmmss(time) == '2023-04-27T17:57:10Z'


def test_format_yyyymmdd_hhmmss_with_jst():
    """Tests ``format_yyyymmdd_hhmmss`` with a datetime in JST.
    """
    jst = pytz.timezone('Asia/Tokyo')
    time = jst.localize(datetime(2023, 4, 28, 2, 59, 1))
    assert format_yyyymmdd_hhmmss(time) == '2023-04-27T17:59:01Z'


def test_format_yyyymmdd_hhmmss_with_naive():
    """Tests ``format_yyyymmdd_hhmmss`` with a naive datetime.
    """
    time = datetime(2023, 4, 27, 17, 57, 10)
    with pytest.raises(ValueError):
        format_yyyymmdd_hhmmss(time)


def test_parse_yyyymmdd_hhmmss_ssssss():
    """Tests ``parse_yyyymmdd_hhmmss_ssssss`` with
    "2023-05-12T11:19:01.123456Z".

    Also makes sure that the timezone is configured.
    """
    time_str = '2023-05-12T11:19:01.123456Z'
    expected = datetime(2023, 5, 12, 11, 19, 1, 123456, tzinfo=timezone.utc)
    parsed = parse_yyyymmdd_hhmmss_ssssss(time_str)
    assert parsed == expected
    assert parsed.tzinfo is not None
    assert parsed.tzinfo.utcoffset(parsed).total_seconds() == 0


def test_parse_yyyymmdd_hhmmss_ssssss_with_invalid_timestamp():
    """Tests ``parse_yyyymmdd_hhmmss_ssssss`` with "11:19:01 on May 12, 2023".
    """
    time_str = '11:19:01 on May 12, 2023'
    with pytest.raises(ValueError):
        parse_yyyymmdd_hhmmss_ssssss(time_str)


def test_parse_yyyymmdd_hhmmss():
    """Tests ``parse_yyyymmdd_hhmmss`` with "2023-05-12T14:45:09Z".

    Also makes sure that the timezone is configured.
    """
    time_str = '2023-05-12T14:45:00Z'
    expected = datetime(2023, 5, 12, 14, 45, 0, tzinfo=timezone.utc)
    parsed = parse_yyyymmdd_hhmmss(time_str)
    assert parsed == expected
    assert parsed.tzinfo is not None
    assert parsed.tzinfo.utcoffset(parsed).total_seconds() == 0


def test_parse_yyyymmdd_hhmmss_with_invalid_timestamp():
    """Tests ``parse_yyyymmdd_hhmmss`` with "14:45:09 on May 12, 2023".
    """
    time_str = '14:45:00 on May 12, 2023'
    with pytest.raises(ValueError):
        parse_yyyymmdd_hhmmss(time_str)
