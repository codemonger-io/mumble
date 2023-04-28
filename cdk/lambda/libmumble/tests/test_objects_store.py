# -*- coding: utf-8 -*-

"""Tests ``libmumble.objects_store``.
"""

from typing import Any, Dict
import pytest
from libmumble.objects_store import (
    dict_as_object_key,
    get_username_from_inbox_key,
    get_username_from_staging_outbox_key,
)


def test_dict_as_object_key_with_valid_dict():
    """Tests ``dict_as_object_key`` with a valid ``dict``.
    """
    obj: Dict[str, Any] = {
        'bucket': 'bucket-for-tests',
        'key': 'inbox/users/kemoto/object.json',
    }
    assert dict_as_object_key(obj) == obj


def test_dict_as_object_key_without_bucket():
    """Tests ``dict_as_object_key`` without "bucket".
    """
    obj: Dict[str, Any] = {
        'key': 'inbox/users/kemoto/object.json',
    }
    with pytest.raises(TypeError):
        dict_as_object_key(obj) == obj


def test_dict_as_object_key_with_non_str_bucket():
    """Tests ``dict_as_object_key`` with non-str "bucket".
    """
    obj: Dict[str, Any] = {
        'bucket': 123,
        'key': 'inbox/users/kemoto/object.json',
    }
    with pytest.raises(TypeError):
        dict_as_object_key(obj) == obj


def test_dict_as_object_key_without_key():
    """Tests ``dict_as_object_key`` without "key".
    """
    obj: Dict[str, Any] = {
        'bucket': 'bucket-for-tests',
    }
    with pytest.raises(TypeError):
        dict_as_object_key(obj) == obj


def test_dict_as_object_key_with_non_str_key():
    """Tests ``dict_as_object_key`` with non-str "key".
    """
    obj: Dict[str, Any] = {
        'bucket': 'bucket-for-tests',
        'key': 123,
    }
    with pytest.raises(TypeError):
        dict_as_object_key(obj) == obj


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


def test_get_username_from_staging_outbox_key_with_valid_key():
    """Tests ``get_username_from_staging_outbox_key`` with a valid staging
    outbox object key.
    """
    key = 'staging/users/kemoto/note.json'
    assert get_username_from_staging_outbox_key(key) == 'kemoto'


def test_get_username_from_staging_outbox_key_with_invalid_key():
    """Tests ``get_username_from_staging_outbox_key`` with an invalid staging
    outbox object key.
    """
    key = 'inbox/users/kemoto/activity.json'
    with pytest.raises(ValueError):
        get_username_from_staging_outbox_key(key)
