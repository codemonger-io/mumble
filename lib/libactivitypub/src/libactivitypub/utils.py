# -*- coding: utf-8 -*-

"""Utilities.
"""

from typing import Any, Tuple


def parse_webfinger_id(account: str) -> Tuple[str, str]:
    """Parses a given WebFinger ID; e.g., Mastodon account ID.

    ``account`` must be in the form "<name>@<domain-name>"; e.g.,
    "gargron@mastodon.social".

    :returns: tuple of the account and domain name.

    :raises ValueError: if ``account`` does not contain an atmark ('@').
    """
    try:
        name, domain = account.split('@', maxsplit=1)
        return name, domain
    except ValueError as exc:
        raise ValueError(
            'WebFinger ID must be in the form "<name>@<domain-name>";'
            f' e.g., "gargron@mastodon.social": {account}',
        ) from exc


def parse_acct_uri(uri: str) -> Tuple[str, str]:
    """Parses a given "acct" URI; e.g., resource URI given to WebFinger.

    ``uri`` must be in the form "acct:<name>@<domain-name>"; e.g.,
    "acct:gargron@mastodon.social".

    :returns: tuple of the account and domain name.

    :raises ValueError: if ``uri`` is not a valid "acct" URI.
    """
    prefix = 'acct:'
    if not uri.startswith(prefix):
        raise ValueError(f'"acct" URI must start with "{prefix}": {uri}')
    return parse_webfinger_id(uri[len(prefix):])


def is_str_or_strs(value: Any) -> bool:
    """Returns if a given value is ``str`` or a sequence of ``str``.
    """
    if isinstance(value, str):
        return True
    try:
        len(value) # should be non-iterator
        return all((isinstance(s, str) for s in value))
    except TypeError:
        return False
