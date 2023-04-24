# -*- coding: utf-8 -*-

"""Tests ``libmumble.user_table``.
"""

from libmumble.user_table import UserTable, get_username_from_user_id
import pytest


def test_get_username_from_user_id_with_valid_id():
    """Tests ``get_username_from_user_id`` with a valid user ID.
    """
    user_id = 'https://mumble.codemonger.io/users/kemoto'
    assert get_username_from_user_id(user_id) == 'kemoto'


def test_get_username_from_user_id_with_trailing_slash():
    """Tests ``get_username_from_user_id`` with a valid user ID ending with
    a slash.
    """
    user_id = 'https://mumble.codemonger.io/users/kemoto/'
    assert get_username_from_user_id(user_id) == 'kemoto'


def test_get_username_from_user_id_with_invalid_id():
    """Tests ``get_username_from_user_id`` with an invalid user ID.
    """
    user_id = 'https://mumble.codemonger.io/users/kemoto/inbox'
    with pytest.raises(ValueError):
        get_username_from_user_id(user_id)


def test_get_username_from_user_id_with_invalid_uri():
    """Tests ``get_username_from_user_id`` with an invalid URI.
    """
    user_id = 'This is not a valid URI!'
    with pytest.raises(ValueError):
        get_username_from_user_id(user_id)


def test_user_table_make_user_key():
    """Tests ``UserTable.make_user_key``.
    """
    assert UserTable.make_user_key('kemoto') == {
        'pk': 'user:kemoto',
        'sk': 'reserved',
    }


def test_user_table_make_follower_key():
    """Tests ``UserTable.make_follower_key``.
    """
    assert UserTable.make_follower_key(
        'kemoto',
        'https://mastodon-japan.net/users/kemoto',
    ) == {
        'pk': 'follower:kemoto',
        'sk': 'https://mastodon-japan.net/users/kemoto',
    }
