# -*- coding: utf-8 -*-

"""Tests ``libmumble.utils``.
"""

from libmumble.utils import to_urlsafe_base64


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
