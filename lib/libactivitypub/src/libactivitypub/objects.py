# -*- coding: utf-8 -*-

"""Provides access to ActivityPub objects.
"""

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, Iterable, Optional, Union
from .activity_stream import get as activity_stream_get


LOGGER = logging.getLogger('libactivitypub.objects')
LOGGER.setLevel(logging.DEBUG)


ACTOR_TYPES = [
    'Application',
    'Group',
    'Organization',
    'Person',
    'Service',
]
"""Possible types for an actor."""


class APObject(ABC):
    """Object in ActivityPub networks.
    """
    @property
    def id(self) -> str: # pylint: disable=invalid-name
        """ID of this object.

        :raises AttributeError: if the property is not implemented, or not
        assigned.
        """
        raise AttributeError('id is not implemented')

    @property
    def type(self) -> str:
        """Type of this object.

        :raises AttributeError: if the property is not implemented.
        """
        raise AttributeError('type is not implemented')

    @abstractmethod
    def to_dict(self, with_context=True) -> Dict[str, Any]:
        """Returns a ``dict`` representation.

        :param bool with_context: retains the JSON-LD context field if this
        flag is ``True``, removes the context field if it is ``False``.
        """


class DictObject(APObject):
    """Object that wraps a ``dict``.
    """
    _underlying: Dict[str, Any]
    """``dict`` representation of the object."""

    def __init__(self, underlying: Dict[str, Any]):
        """Wraps a given ``dict``.

        :raises ValueError: if ``underlying`` does not have ``type``.

        :raises TypeError: if ``underlying`` has non-str ``id``,
        or if ``underlying`` has a non-str ``type``.
        """
        if 'id' in underlying and not isinstance(underlying['id'], str):
            raise TypeError(
                f'id must be str but {type(underlying["id"])}',
            )
        if 'type' not in underlying:
            raise ValueError('invalid object: missing type')
        if not isinstance(underlying['type'], str):
            raise TypeError(
                f'type must be str but {type(underlying["type"])}',
            )
        self._underlying = underlying

    @property
    def id(self) -> str:
        if 'id' not in self._underlying:
            raise AttributeError('id is not assigned')
        return self._underlying['id']

    @property
    def type(self) -> str:
        return self._underlying['type']

    def to_dict(self, with_context=True) -> Dict[str, Any]:
        if with_context or '@context' not in self._underlying:
            return self._underlying
        underlying = self._underlying.copy()
        del underlying['@context']
        return underlying

    @staticmethod
    def resolve(obj: Union[str, Dict[str, Any]]) -> 'DictObject':
        """Resolves an object.

        ``obj`` may be a URI, a link object, or ``dict`` representation of the
        object itself.

        If ``obj`` is a URI or link, makes an HTTP request to resolve it.
        Otherwise, wraps ``obj`` with ``DictObject``.

        :raises requests.HTTPError: if an HTTP request fails.

        :raises ValueError: if the ``obj`` does not represent a valid object.
        """
        if isinstance(obj, str):
            LOGGER.debug('requesting: %s', obj)
            return DictObject(activity_stream_get(obj))
        if obj.get('type') == 'Link':
            link = Link(obj)
            LOGGER.debug('requesting: %s', link.href)
            return DictObject(activity_stream_get(link.href))
        return DictObject(obj)


class Link(DictObject):
    """Wraps a link object.
    """
    def __init__(self, underlying: Dict[str, Any]):
        """Wraps a given ``dict``.

        :raises ValueError: if ``underlying`` has no ``href``, or if ``type``
        is not "Link", or if ``underlying`` is an invalid object.

        :raises TypeError: if ``underlying`` has a non-str ``href``.
        """
        super().__init__(underlying)
        if self.type != 'Link':
            raise ValueError('type must be Link but {self.type}')
        if 'href' not in self._underlying:
            raise ValueError('invalid link object: missing link')
        if not isinstance(self._underlying['href'], str):
            raise TypeError(
                f'href must be str but {type(self._underlying["href"])}',
            )

    @property
    def href(self) -> str:
        """href field value.
        """
        return self._underlying['href']


class ObjectStore:
    """Stores objects.

    Works as a dictionary of ActivityPub objects.
    """
    _dict: Dict[str, APObject]
    """Maps an object ID to the instance."""

    def __init__(self, objects: Iterable[APObject]):
        """Initializes with already resolved objects.
        """
        self._dict = { o.id: o for o in objects }

    def get(self, id_: str) -> Optional[APObject]:
        """Obtains the object associated with a given ID in this store.
        """
        return self._dict.get(id_)

    def add(self, obj: APObject):
        """Adds a given object to this store.

        :raises AttributeError: if ``obj`` has no ID.
        """
        self._dict[obj.id] = obj


class Reference:
    """Reference to an object.
    """
    ref: Union[str, Dict[str, Any]]
    """Reference to an object."""

    def __init__(self, ref: Union[str, Dict[str, Any]]):
        """Wraps a reference to an object.

        ``ref`` may be a URI, link object, or ``dict`` representation of the
        object itself.

        :raises ValueError: if ``ref`` does not have ``type`` when ``ref`` is
        a ``dict`` representation, or if ``ref`` does not have ``href`` when
        ``ref`` is a link object, or if ``ref`` does not have ``id`` when
        ``ref`` represents the object itself.

        :raises TypeError: if ``ref`` is a "Link" but has a non-str ``href``,
        or if ``ref`` is an object itself but has a non-str ``id``.
        """
        if not isinstance(ref, str):
            if 'type' not in ref:
                raise ValueError('dict ref must have type')
            if ref['type'] == 'Link':
                if 'href' not in ref:
                    raise ValueError('link ref must have href')
                if not isinstance(ref['href'], str):
                    raise TypeError('href must be str but {type(ref["href"])}')
            else:
                if 'id' not in ref:
                    raise ValueError('object must have id')
                if not isinstance(ref['id'], str):
                    raise TypeError('id must be str but {type(ref["id"])}')
        self.ref = ref

    @property
    def id(self) -> str: # pylint: disable=invalid-name
        """ID of the object.
        """
        if isinstance(self.ref, str):
            return self.ref
        if self.ref['type'] == 'Link':
            return self.ref['href']
        return self.ref['id']
