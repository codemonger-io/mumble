# -*- coding: utf-8 -*-

"""Tests ``libactivitypub.utils``.
"""

from libactivitypub.utils import (
    is_sequence_of,
    is_str_or_strs,
    parse_acct_uri,
    parse_webfinger_id,
)
import pytest


def test_parse_webfinger_id_with_valid_account():
    """Tests ``parse_webfinger_id`` with a valid account name
    ("gargron@mastodon.social").
    """
    assert parse_webfinger_id('gargron@mastodon.social') == ('gargron', 'mastodon.social')


def test_parse_webfinger_id_without_atmark():
    """Tests ``parse_webfinger_id`` with an account name without an atmark
    ("gargron").
    """
    with pytest.raises(ValueError):
        parse_webfinger_id('gargron')


def test_parse_acct_uri_with_valid_uri():
    """Tests ``parse_acct_uri`` with a valid URI
    ("acct:gargron@mastodon.social").
    """
    assert parse_acct_uri('acct:gargron@mastodon.social') == ('gargron', 'mastodon.social')


def test_parse_acct_uri_without_acct_scheme():
    """Tests ``parse_acct_uri`` with a string without the "acct" scheme
    ("gargron@mastodon.social").
    """
    with pytest.raises(ValueError):
        parse_acct_uri('gargron@mastodon.social')


def test_parse_acct_uri_without_atmark():
    """Tests ``parse_acct_uri`` with a string without an atmark
    ("acct:gargron").
    """
    with pytest.raises(ValueError):
        parse_acct_uri('acct:gargron')


def test_is_str_or_strs_with_str():
    """Tests ``is_str_or_strs`` with a ``str``.
    """
    assert is_str_or_strs('string')


def test_is_str_or_strs_with_str_list():
    """Tests ``is_str_or_strs`` with a list of ``str``.
    """
    assert is_str_or_strs(['one', 'two', 'three'])


def test_is_str_or_strs_with_int():
    """Tests ``is_str_or_strs`` with an ``int``.
    """
    assert not is_str_or_strs(123)


def test_is_str_or_strs_with_int_list():
    """Tests ``is_str_or_strs`` with a list of ``int``.
    """
    assert not is_str_or_strs([1, 2, 3])


def test_is_str_or_strs_with_str_iterator():
    """Tests ``is_str_or_strs`` with an iterator of ``str``.
    """
    assert not is_str_or_strs(iter(['one', 'two', 'three']))


def test_is_str_or_strs_with_str_to_str_dict():
    """Tests ``is_str_or_strs`` with a ``dict`` that maps ``str`` to ``str``.
    """
    assert not is_str_or_strs({'one': '1', 'two': '2', 'three': '3'})


def test_is_sequence_of():
    """Tests ``is_sequence_of`` with a list.
    """
    assert is_sequence_of([1, 2, 3], lambda x: x > 0)


def test_is_sequence_of_with_unsatisfied_predicate():
    """Tests ``is_sequence_of`` with a list that includes an item not
    satisfying the predicate.
    """
    assert not is_sequence_of([1, 0, 3], lambda x: x > 0)


def test_is_sequence_of_with_iterator():
    """Tests ``is_sequence_of`` with an iterator.
    """
    assert not is_sequence_of(iter([1, 2, 3]), lambda _: True)


def test_is_sequence_of_with_dict():
    """Tests ``is_sequence_of`` with a ``dict``.
    """
    assert not is_sequence_of(
        { 1: 'one', 2: 'two', 3: 'three' },
        lambda _: True,
    )


def test_is_sequence_of_with_int():
    """Tests ``is_sequence_of`` with an ``int``.
    """
    assert not is_sequence_of(123, lambda _: True)
