# -*- coding: utf-8 -*-

"""Provides miscellaneous utilities.
"""

from datetime import datetime, timezone
from itertools import islice
from typing import Iterable, List, TypeVar
from urllib.parse import quote
import pytz


# format string for "yyyy-mm-ddTHH:MM:ss.SSSSSSZ"
FORMAT_STRING_YYYYMMDD_HHMMSS_SSSSSS = '%Y-%m-%dT%H:%M:%S.%fZ'

# format string for "yyyy-mm-ddTHH:MM:ssZ"
FORMAT_STRING_YYYYMMDD_HHMMSS = '%Y-%m-%dT%H:%M:%SZ'


def urlencode(text: str) -> str:
    """Converts a given string into a URL-encoded string.

    Replaces also slashes ('/').
    """
    return quote(text, safe='')


def to_urlsafe_base64(b64: str) -> str:
    """Converts a standard Base64-encoded string into a URL-safe string.

    Replaces '+' with '-', and '/' with '_'.
    Removes trailing '='.
    """
    return b64.rstrip('=').replace('+', '-').replace('/', '_')


T = TypeVar('T')

def chunk(sequence: Iterable[T], size: int) -> Iterable[List[T]]:
    """Splits a given sequence into chunks of a specified size.
    """
    iter_seq = iter(sequence)
        # makes sure that the input is an iterator,
        # otherwise, ends up with an infinite loop
    return iter(lambda: list(islice(iter_seq, size)), [])


def format_datetime_in_utc(format: str, time: datetime) -> str: # pylint: disable=redefined-builtin
    """Formats a given datetime in a specified format.

    The timezone is adjusted into UTC.

    :raises ValueError: if ``time`` is naive.
    """
    if time.tzinfo is None:
        raise ValueError('datetime must be timezone-aware')
    offset = time.tzinfo.utcoffset(time)
    if offset is None:
        raise ValueError('datetime must be timezone-aware')
    if offset.total_seconds() != 0:
        time = time.astimezone(timezone.utc)
    return time.strftime(format)


def format_yyyymmdd_hhmmss_ssssss(time: datetime) -> str:
    """Formats a given datetime into "yyyy-mm-ddTHH:MM:ss.SSSSSSZ" form.

    The timezone is adjusted into UTC.

    :raises ValueError: if ``time`` is naive.
    """
    return format_datetime_in_utc(FORMAT_STRING_YYYYMMDD_HHMMSS_SSSSSS, time)


def format_yyyymmdd_hhmmss(time: datetime) -> str:
    """Formats a given datetime into "yyyy-mm-ddTHH:MM:ssZ".

    The timezone is adjusted into UTC.

    :raises ValueError: if ``time`` is naive.
    """
    return format_datetime_in_utc(FORMAT_STRING_YYYYMMDD_HHMMSS, time)


def current_yyyymmdd_hhmmss_ssssss() -> str:
    """Returns the current timestamp in the form: "yyyy-mm-ddTHH:MM:ss.SSSSSSZ".
    """
    return format_yyyymmdd_hhmmss_ssssss(datetime.now(tz=timezone.utc))


def current_yyyymmdd_hhmmss() -> str:
    """Returns the current timestamp in the form: "yyyy-mm-ddTHH:MM:ssZ".
    """
    return format_yyyymmdd_hhmmss(datetime.now(tz=timezone.utc))


def parse_yyyymmdd_hhmmss_ssssss(time_str: str) -> datetime:
    """Parses a given timestamp represented in "yyyy-mm-ddTHH:MM:ss.SSSSSSZ"
    form.

    The timezone is assumed to be UTC.

    :raises ValueError: if ``time_str`` is malformed.
    """
    time = datetime.strptime(time_str, FORMAT_STRING_YYYYMMDD_HHMMSS_SSSSSS)
    return pytz.utc.localize(time)


def parse_yyyymmdd_hhmmss(time_str: str) -> datetime:
    """Parses a given timestamp represented in "yyyy-mm-ddTHH:MM:ssZ" form.

    The timezone is assumed to be UTC.

    :raises ValueError: if ``time_str`` is malformed.
    """
    time = datetime.strptime(time_str, FORMAT_STRING_YYYYMMDD_HHMMSS)
    return pytz.utc.localize(time)
