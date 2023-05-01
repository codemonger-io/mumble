# -*- coding: utf-8 -*-

"""Tests ``libmumble.id_scheme``.
"""

from libmumble.id_scheme import (
    parse_user_activity_id,
    parse_user_post_id,
    split_user_id,
)
import pytest


def test_split_user_id_without_remaining():
    """Tests ``split_user_id`` without a remaining part.
    """
    user_id = 'https://mumble.codemonger.io/users/kemoto'
    assert split_user_id(user_id) == ('mumble.codemonger.io', 'kemoto', '')


def test_split_user_id_with_remaining():
    """Tests ``split_user_id`` with a remainig part.
    """
    user_id = 'https://mumble.codemonger.io/users/kemoto/activities/abcdefg'
    assert split_user_id(user_id) == (
        'mumble.codemonger.io',
        'kemoto',
        '/activities/abcdefg',
    )


def test_split_user_id_without_host():
    """Tests ``split_user_id`` without the host part.
    """
    user_id = '/users/kemoto'
    with pytest.raises(ValueError):
        split_user_id(user_id)


def test_split_user_id_with_non_uri():
    """Tests ``split_user_id`` with a non-URI.
    """
    user_id = 'This is not a valid URI!'
    with pytest.raises(ValueError):
        split_user_id(user_id)


def test_parse_user_activity_id_with_valid_id():
    """Tests ``parse_user_activity_id`` with a valid activity ID.
    """
    activity_id = 'https://mumble.codemonger.io/users/kemoto/activities/0000-0000'
    assert parse_user_activity_id(activity_id) == (
        'mumble.codemonger.io',
        'kemoto',
        '0000-0000',
    )


def test_parse_user_activity_id_with_trailing_slash():
    """Tests ``parse_user_activity_id`` with a trailing slash (valid).
    """
    activity_id = 'https://mumble.codemonger.io/users/kemoto/activities/0000-0000/'
    assert parse_user_activity_id(activity_id) == (
        'mumble.codemonger.io',
        'kemoto',
        '0000-0000',
    )


def test_parse_user_activity_id_with_non_activity_id():
    """Tests ``parse_user_activity_id`` with a non-activity ID.
    """
    activity_id = 'https://mumble.codemonger.io/users/kemoto/posts/0000-0000'
    with pytest.raises(ValueError):
        parse_user_activity_id(activity_id)


def test_parse_user_activity_id_with_extra_segment():
    """Tests ``parse_user_activity_id`` with an extra segment.
    """
    activity_id = 'https://mumble.codemonger.io/users/kemoto/activities/0000-0000/extra'
    with pytest.raises(ValueError):
        parse_user_activity_id(activity_id)


def test_parse_user_post_id_with_valid_id():
    """Tests ``parse_user_post_id`` with a valid post ID.
    """
    post_id = 'https://mumble.codemonger.io/users/kemoto/posts/0000-0000'
    assert parse_user_post_id(post_id) == (
        'mumble.codemonger.io',
        'kemoto',
        '0000-0000',
    )


def test_parse_user_post_id_with_trailing_slash():
    """Tests ``parse_user_post_id`` with a trailing slash (valid).
    """
    post_id = 'https://mumble.codemonger.io/users/kemoto/posts/0000-0000/'
    assert parse_user_post_id(post_id) == (
        'mumble.codemonger.io',
        'kemoto',
        '0000-0000',
    )


def test_parse_user_post_id_with_non_post_id():
    """Tests ``parse_user_post_id`` with a non-activity ID.
    """
    post_id = 'https://mumble.codemonger.io/users/kemoto/activities/0000-0000'
    with pytest.raises(ValueError):
        parse_user_post_id(post_id)


def test_parse_user_post_id_with_extra_segment():
    """Tests ``parse_user_post_id`` with an extra segment.
    """
    post_id = 'https://mumble.codemonger.io/users/kemoto/posts/0000-0000/extra'
    with pytest.raises(ValueError):
        parse_user_post_id(post_id)
