# -*- coding: utf-8 -*-

"""Utilities.
"""

from typing import Tuple


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
