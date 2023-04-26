# -*- coding: utf-8 -*-

"""Access to actors on ActivityPub networks.
"""

from functools import cached_property
import logging
from typing import Any, Dict, TypedDict
import requests
from .activity_streams import (
    DEFAULT_REQUEST_TIMEOUT,
    get as activity_streams_get,
)
from .inbox import Inbox
from .mime_types import ACTIVITY_STREAMS_MIME_TYPES
from .objects import DictObject
from .outbox import Outbox
from .utils import parse_webfinger_id


LOGGER = logging.getLogger('libactivitypub.actor')
LOGGER.setLevel(logging.DEBUG)


class PublicKey(TypedDict):
    """Public key.
    """
    id: str
    """ID of the public key."""
    owner: str
    """Owner of the public key."""
    publicKeyPem: str
    """PEM representation of the public key."""


def dict_as_public_key(d: Dict[str, Any]) -> PublicKey: # pylint: disable=invalid-name
    """Casts a given ``dict`` as a ``PublicKey``.

    :raises TypeError: if ``d`` does not conform to ``PublicKey``.
    """
    if not isinstance(d.get('id'), str):
        raise TypeError(f'id must be str but {type(d.get("id"))}')
    if not isinstance(d.get('owner'), str):
        raise TypeError(f'owner must be str but {type(d.get("owner"))}')
    if not isinstance(d.get('publicKeyPem'), str):
        raise TypeError(
            f'publicKeyPem must be str but {type(d.get("publicKeyPem"))}',
        )
    # unfortunately, the above checks cannot convince mypy that d is PublicKey
    return d # type: ignore


class WebFinger:
    """Wraps WebFinger query results.
    """
    account: str
    """WebFinger ID of the account."""

    def __init__(self, account: str, underlying: Dict[str, Any]):
        """Initializes with given WebFinger query results.
        """
        self.account = account
        self._underlying = underlying

    @staticmethod
    def finger(account: str) -> 'WebFinger':
        """Queries a WebFinger for a given account.

        :raises ValueError: if ``account`` is not a valid WebFinger ID.

        :raises requests.HTTPError: if an HTTP request fails.
        """
        _, domain = parse_webfinger_id(account)
        endpoint = f'https://{domain}/.well-known/webfinger?resource=acct:{account}'
        LOGGER.debug('GETting: %s', endpoint)
        res = requests.get(
            endpoint,
            headers={
                'Accept': 'application/json',
            },
            timeout=DEFAULT_REQUEST_TIMEOUT,
        )
        res.raise_for_status()
        underlying = res.json()
        return WebFinger(account, underlying)

    @cached_property
    def actor_uri(self):
        """Actor URI (ID).

        :raises AttributeError: if no actor URI is provide.
        """
        try:
            links = self._underlying['links']
            links = [
                l for l in links if l.get('type') in ACTIVITY_STREAMS_MIME_TYPES
            ]
            if len(links) > 1:
                LOGGER.warning(
                    'there are more than one actor URIs: %d',
                    len(links),
                )
                links = [l for l in links if l.get('rel') == 'self']
                if len(links) > 1:
                    # warns but chooses the first link
                    LOGGER.warning(
                        'there are more than one "self" actor URIs: %d',
                        len(links),
                    )
            return links[0]['href']
        except (IndexError, KeyError) as exc:
            raise AttributeError('no Actor URI is provided') from exc


class Actor(DictObject):
    """Actor on ActivityPub networks.
    """
    @staticmethod
    def resolve_uri(actor_uri: str) -> 'Actor':
        """Resolves the actor at a given URI (ID).

        :raises requests.HTTPError: if an HTTP request fails.

        :raises ValueError: if the resolved object is not a valid actor.
        """
        LOGGER.debug('requesting actor: %s', actor_uri)
        underlying = activity_streams_get(actor_uri)
        return Actor(underlying)

    @staticmethod
    def resolve_webfinger_id(account: str) -> 'Actor':
        """Resolves the actor associated with a given WebFinger ID; e.g.,
        Mastodon account ID.

        :raises ValueError: if ``account`` is not a valid WebFinger ID,
        or if no ActivityPub actor is associated with ``account``.

        :raises requests.HTTPError: if an HTTP request fails.
        """
        finger = WebFinger.finger(account)
        try:
            LOGGER.debug('requesting actor: %s', finger.actor_uri)
            underlying = activity_streams_get(finger.actor_uri)
            return Actor(underlying)
        except AttributeError as exc:
            raise ValueError(f'no actor associated with "{account}"') from exc

    @property
    def inbox(self) -> Inbox:
        """Inbox of the actor.

        :raises AttributeError: if no inbox is provided.
        """
        if 'inbox' not in self._underlying:
            raise AttributeError('no inbox is provided')
        return Inbox(self._underlying['inbox'])

    @property
    def outbox(self) -> Outbox:
        """Outbox of the actor.

        :raises AttributeError: if no outbox is provided.
        """
        if 'outbox' not in self._underlying:
            raise AttributeError('no outbox is provided')
        return Outbox(self._underlying['outbox'])

    @property
    def public_key(self) -> PublicKey:
        """Public key of the actor.

        Mastodon compliant actor must have a public key.

        :raises AttributeError: if no public key is provided.

        :raises TypeError: if the provided public key is invalid.
        """
        if 'publicKey' not in self._underlying:
            raise AttributeError('no public key is provided')
        return dict_as_public_key(self._underlying['publicKey'])
