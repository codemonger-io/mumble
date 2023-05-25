# -*- coding: utf-8 -*-

"""Tests ``libmumble.objects_store``.
"""

from typing import Any, Dict
import pytest
from libmumble.objects_store import (
    dict_as_object_key,
    get_username_from_inbox_key,
    get_username_from_outbox_key,
    get_username_from_staging_outbox_key,
    parse_user_inbox_key,
    parse_user_object_key,
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


def test_parse_user_inbox_key_with_extension():
    """Tests ``parse_user_inbox_key`` with a valid inbox object key with an
    extension.
    """
    key = 'inbox/users/kemoto/abcdefg.json'
    expected = ('kemoto', 'abcdefg', '.json')
    assert parse_user_inbox_key(key) == expected


def test_parse_user_inbox_key_without_extension():
    """Tests ``parse_user_inbox_key`` with a valid inbox object key without an
    extension.
    """
    key = 'inbox/users/kemoto/abcdefg'
    expected = ('kemoto', 'abcdefg', '')
    assert parse_user_inbox_key(key) == expected


def test_parse_user_inbox_key_without_unique_part():
    """Tests ``parse_user_inbox_key`` without the unique part and extension.
    """
    key = 'inbox/users/kemoto'
    with pytest.raises(ValueError):
        parse_user_inbox_key(key)


def test_parse_user_inbox_key_with_non_inbox():
    """Tests ``parse_user_inbox_key`` with a key does not represent an inbox.
    """
    key = 'outbox/users/kemoto/activity.json'
    with pytest.raises(ValueError):
        parse_user_inbox_key(key)


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


def test_get_username_from_outbox_key_with_valid_key():
    """Tests ``get_username_from_outbox_key`` with a valid outbox object key.
    """
    key = 'outbox/users/kemoto/activity.json'
    assert get_username_from_outbox_key(key) == 'kemoto'


def test_get_username_from_outbox_key_with_invalid_key():
    """Tests ``get_username_from_outbox_key`` with an invalid outbox object
    key.
    """
    key = 'staging/users/kemoto/note.json'
    with pytest.raises(ValueError):
        get_username_from_outbox_key(key)


def test_parse_user_object_key_with_post_key():
    """Tests ``parse_user_object_key`` with a valid post key.
    """
    key = 'objects/users/kemoto/posts/abcdefg.json'
    expected = ('kemoto', 'posts', 'abcdefg', '.json')
    assert parse_user_object_key(key) == expected


def test_parse_user_object_key_with_media_key():
    """Tests ``parse_user_object_key`` with a valid media key.
    """
    key = 'objects/users/kemoto/media/logo.png'
    expected = ('kemoto', 'media', 'logo', '.png')
    assert parse_user_object_key(key) == expected


def test_parse_user_object_key_without_unique_part():
    """Tests ``parse_user_object_key`` without the unique part.
    """
    key = 'objects/users/kemoto/posts/'
    with pytest.raises(ValueError):
        parse_user_object_key(key)
