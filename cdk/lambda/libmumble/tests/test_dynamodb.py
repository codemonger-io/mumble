# -*- coding: utf-8 -*-

"""Tests ``dynamodb`` submodule.
"""

from libmumble.dynamodb import dict_as_primary_key
import pytest


def test_dict_as_primary_key():
    """Tests ``dict_as_primary_key`` with a valid key.
    """
    key = {
        'pk': 'the primary key',
        'sk': 'the secondary key',
    }
    assert dict_as_primary_key(key) == key


def test_dict_as_primary_key_without_pk():
    """Tests ``dict_as_primary_key`` without "pk".
    """
    key = {
        'sk': 'the secondary key',
    }
    with pytest.raises(TypeError):
        dict_as_primary_key(key)


def test_dict_as_primary_key_with_non_str_pk():
    """Tests ``dict_as_primary_key`` with a non-str "pk".
    """
    key = {
        'pk': 345,
        'sk': 'the secondary key',
    }
    with pytest.raises(TypeError):
        dict_as_primary_key(key)


def test_dict_as_primary_key_withoug_sk():
    """Tests ``dict_as_primary_key`` without "sk".
    """
    key = {
        'pk': 'the primary key',
    }
    with pytest.raises(TypeError):
        dict_as_primary_key(key)


def test_dict_as_primary_key_with_non_str_sk():
    """Tests ``dict_as_primary_key`` with a non-str "sk".
    """
    key = {
        'pk': 'the primary key',
        'sk': 345,
    }
    with pytest.raises(TypeError):
        dict_as_primary_key(key)
