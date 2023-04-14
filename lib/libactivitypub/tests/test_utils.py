# -*- coding: utf-8 -*-

"""Tests ``libactivitypub.utils``.
"""

from libactivitypub.utils import parse_acct_uri, parse_webfinger_id
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
