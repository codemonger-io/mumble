# -*- coding: utf-8 -*-

"""Provides access to ActivityPub objects.
"""

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, Iterable, List, Optional, TypeVar, Type, Union
from uuid6 import uuid7
from .activity_streams import (
    ACTIVITY_STREAMS_PUBLIC_ADDRESS,
    get as activity_streams_get,
)
from .utils import is_str_or_strs


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

    @property
    def published(self) -> str:
        """Timestamp in UTC when this object was published.

        Must be like "2023-05-17T10:31:00Z".

        :raises AttributeError: if the property is not implemented, or not
        assigned.
        """
        raise AttributeError('published is not implemented')

    @property
    def to(self) -> Union[str, List[str]]: # pylint: disable=invalid-name
        """Public primary audience of this object.

        :raises AttributeError: if the property is not implemented, or not
        assigned.
        """
        raise AttributeError('to is not implemented')

    @property
    def cc(self) -> Union[str, List[str]]: # pylint: disable=invalid-name
        """Public secondary audience of this object.

        :raises AttributeError: if the property is not implemented, or not
        assigned.
        """
        raise AttributeError('cc is not implemented')

    @property
    def bcc(self) -> Union[str, List[str]]:
        """Private secondary audience of this object.

        :raises AttributeError: if the property is not implemented, or not
        assigned.
        """
        raise AttributeError('bcc is not implemented')

    @property
    def in_reply_to(self) -> 'Reference':
        """In-reply-to.

        :raises AttributeError: if the property is not implemented, or not
        assigned.
        """
        raise AttributeError('in_reply_to is not implemented')

    @abstractmethod
    def to_dict(self, with_context=True) -> Dict[str, Any]:
        """Returns a ``dict`` representation.

        :param bool with_context: retains the JSON-LD context field if this
        flag is ``True``, removes the context field if it is ``False``.
        """

    def is_public(self) -> bool:
        """Returns if this object is public.

        An object is public if ``to`` or ``cc`` contain the ActivityStreams'
        public address.

        Returns ``False`` if this object has neither of ``to`` and ``cc``.
        """
        def contains_public(addresses: Union[str, List[str]]) -> bool:
            if isinstance(addresses, str):
                return addresses == ACTIVITY_STREAMS_PUBLIC_ADDRESS
            return ACTIVITY_STREAMS_PUBLIC_ADDRESS in addresses
        if hasattr(self, 'to') and contains_public(self.to):
            return True
        if hasattr(self, 'cc') and contains_public(self.cc):
            return True
        return False


T = TypeVar('T', bound='DictObject')


class DictObject(APObject):
    """Object that wraps a ``dict``.
    """
    _underlying: Dict[str, Any]
    """``dict`` representation of the object."""

    def __init__(self, underlying: Dict[str, Any]):
        """Wraps a given ``dict``.

        :raises TypeError: if ``underlying`` has non-str "id",
        or if ``underlying`` does not have "type",
        or if ``underlying`` has a non-str "type",
        or if ``underlying`` has a non-str "published",
        or if ``underlying`` has an invalid "to",
        or if ``underlying`` has an invalid "cc",
        or if ``underlying`` has an invalid "bcc",
        or if ``underlying`` has an invalid "inReplyTo".
        """
        if 'id' in underlying and not isinstance(underlying['id'], str):
            raise TypeError(
                f'id must be str but {type(underlying["id"])}',
            )
        if 'type' not in underlying:
            raise TypeError('invalid object: missing type')
        if not isinstance(underlying['type'], str):
            raise TypeError(
                f'type must be str but {type(underlying["type"])}',
            )
        if (
            'published' in underlying
            and not isinstance(underlying['published'], str)
        ):
            raise TypeError(
                f'published must be str but {type(underlying["published"])}',
            )
        if 'to' in underlying and not is_str_or_strs(underlying['to']):
            raise TypeError(f'to must be str(s) but {type(underlying["to"])}')
        if 'cc' in underlying and not is_str_or_strs(underlying['cc']):
            raise TypeError(f'cc must be str(s) but {type(underlying["cc"])}')
        if 'bcc' in underlying and not is_str_or_strs(underlying["bcc"]):
            raise TypeError(
                f'bcc must be str(s) but {type(underlying["bcc"])}',
            )
        if 'inReplyTo' in underlying:
            Reference(underlying['inReplyTo'])
        self._underlying = underlying

    def set_jsonld_context(self, context: str):
        """Sets the JSON+LD context ("@context").
        """
        self._underlying['@context'] = context

    @property
    def id(self) -> str:
        if 'id' not in self._underlying:
            raise AttributeError('id is not assigned')
        return self._underlying['id']

    @id.setter
    def id(self, value: str):
        self._underlying['id'] = value

    @property
    def type(self) -> str:
        return self._underlying['type']

    @property
    def published(self) -> str:
        if 'published' not in self._underlying:
            raise AttributeError('published is not assigned')
        return self._underlying['published']

    @published.setter
    def published(self, published: str):
        """Sets "published" of this object.
        """
        self._underlying['published'] = published

    @property
    def to(self) -> Union[str, List[str]]:
        if 'to' not in self._underlying:
            raise AttributeError('to is not assigned')
        return self._underlying['to']

    @to.setter
    def to(
        self,
        to: Union[str, List[str]], # pylint: disable=invalid-name
    ):
        """Sets "to" of this object.
        """
        self._underlying['to'] = to # pylint: disable=invalid-name

    @property
    def cc(self) -> Union[str, List[str]]:
        if 'cc' not in self._underlying:
            raise AttributeError('cc is not assigned')
        return self._underlying['cc']

    @cc.setter
    def cc(
        self,
        cc: Union[str, List[str]], # pylint: disable=invalid-name
    ):
        """Sets "cc" of this object.
        """
        self._underlying['cc'] = cc # pylint: disable=invalid-name

    @property
    def bcc(self) -> Union[str, List[str]]:
        if 'bcc' not in self._underlying:
            raise AttributeError('bcc is not assigned')
        return self._underlying['bcc']

    @bcc.setter
    def bcc(self, bcc: Union[str, List[str]]):
        """Sets "bcc" of this object.
        """
        self._underlying['bcc'] = bcc

    @property
    def in_reply_to(self) -> 'Reference':
        """In-reply-to of this object.
        """
        if 'inReplyTo' not in self._underlying:
            raise AttributeError('in_reply_to is not assigned')
        return Reference(self._underlying['inReplyTo'])

    def cast(self, cls: Type[T]) -> T:
        """Casts this object as a given subclass.

        :raises ValueError: if this object cannot be represented as ``cls``.

        :raises TypeError: if this object incompatible with ``cls``.
        """
        return cls(self._underlying)

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

        :raises requests.Timeout: if an HTTP request times out.

        :raises ValueError: if the ``obj`` does not represent a valid object.
        """
        if isinstance(obj, str):
            LOGGER.debug('requesting: %s', obj)
            return DictObject(activity_streams_get(obj))
        if obj.get('type') == 'Link':
            link = Link(obj)
            LOGGER.debug('requesting: %s', link.href)
            return DictObject(activity_streams_get(link.href))
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

    def resolve(self) -> DictObject:
        """Resolves the object associated with this reference.

        Simply wraps the underlying ``dict``, if this reference wraps a
        ``dict`` representing an object itself.
        Otherwise, obtains the object via an HTTP request.

        :raises requests.HTTPError: if an HTTP request to obtain the object
        fails.

        :raises requests.Timeout: if an HTTP request to obtain the object
        times out.

        :raises TypeError: if the resolved object is invalid.

        :raises ValueError: if the resolved object is invalid.
        """
        if isinstance(self.ref, str):
            return DictObject.resolve(self.ref)
        if self.ref['type'] == 'Link':
            return DictObject.resolve(self.ref['href'])
        return DictObject(self.ref)


def generate_id() -> str:
    """Generates a random ID for an object.

    UUID v7 is used to generate an ID.

    :returns: string representation of a UUID like
    "00000000-0000-0000-0000-00000000".
    """
    return str(uuid7())
