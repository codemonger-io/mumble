# -*- coding: utf-8 -*-

"""Tests ``libmumble.utils``.
"""

from datetime import datetime, timezone
from libmumble.utils import format_yyyymmdd_hhmmss_ssssss, to_urlsafe_base64
import pytest
import pytz


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
