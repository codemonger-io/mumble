# -*- coding: utf-8 -*-

"""Tests ``libmumble.objects_store``.
"""

import pytest
from libmumble.objects_store import get_username_from_inbox_key


def test_get_username_from_inbox_key_with_valid_key():
    """Tests ``get_username_from_inbox_key`` with a valid inbox object key.
    """
    key = 'inbox/users/kemoto/activity.json'
    assert get_username_from_inbox_key(key) == 'kemoto'


def test_get_username_from_inbox_key_with_invalid_key():
    """Tests ``get_username_from_inbox_key`` with an invalid inbox object key.
    """
    key = 'outbox/users/kemoto/activity.json'
    with pytest.raises(ValueError):
        get_username_from_inbox_key(key)
