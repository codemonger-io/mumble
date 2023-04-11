# -*- coding: utf-8 -*-

"""Tests ``libactivitypub.utils``.
"""

from libactivitypub.utils import parse_webfinger_id
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
