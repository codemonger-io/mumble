# -*- coding: utf-8 -*-

"""Provides access to activities.
"""

from abc import abstractmethod
import logging
from typing import Any, Dict, Iterable, Optional, Union
from .objects import ACTOR_TYPES, APObject, DictObject, Reference, ObjectStore


LOGGER = logging.getLogger('libactivitypub.activity')
LOGGER.setLevel(logging.DEBUG)

RESERVED_TARGETS = [
    'https://www.w3.org/ns/activitystreams#Public',
]


class Activity(DictObject):
    """Wraps an activity.
    """
    def __init__(self, underlying: Dict[str, Any]):
        """Wraps a given ``dict`` representing an activity.

        :raises ValueError: if ``underlying`` does not have ``id``, ``type``,
        or ``actor``.
        """
        super().__init__(underlying)
        if 'actor' not in underlying:
            raise ValueError('invalid activity object: actor is missing')
        self._underlying = underlying

    @staticmethod
    def parse_object(obj: Dict[str, Any]) -> 'Activity':
        """Parses a given activity object.

        :raises ValueError: if ``obj`` does not represent an activity object.
        """
        obj_type = obj.get('type')
        # TODO: tabularize the following
        if obj_type == 'Announce':
            return Announce.parse_object(obj)
        if obj_type == 'Create':
            return Create.parse_object(obj)
        if obj_type is not None:
            raise ValueError(f'unsupported activity type: {obj_type}')
        raise ValueError('invalid object: type is missing')

    @property
    def id(self) -> str:
        return self._underlying['id']

    @property
    def type(self) -> str:
        return self._underlying['type']

    @abstractmethod
    def resolve_objects(self, object_store: ObjectStore):
        """Resolves objects referenced in this activity.

        This method resolves the actor.

        Subclasses must override this method but can call this method to deal
        with ``actor`` field.

        :raises ValueError: if the actor has an invalid type.
        """
        actor_ref = Reference(self._underlying['actor'])
        actor: Optional[APObject] = object_store.get(actor_ref.id)
        if actor is None:
            actor = DictObject.resolve(actor_ref.ref)
        if actor.type not in ACTOR_TYPES:
            raise ValueError(f'invalid actor type: {actor.type}')
        object_store.add(actor)


# TODO: `to` and `cc` are standard fields in an Object.
#       should this be here?
# TODO: what about `bto`?
class MessageActivity(Activity):
    """Activity that may have ``to`` and ``cc`` fields.
    """
    @abstractmethod
    def resolve_objects(self, object_store: ObjectStore):
        """Resolves actors referenced in ``to`` and ``cc`` fields.

        Subclasses still must implement this method but can call this method
        to deal with ``to`` and ``cc`` fields.
        """
        super().resolve_objects(object_store)
        if 'to' in self._underlying:
            MessageActivity.resolve_targets(
                self._underlying['to'],
                object_store,
            )
        if 'cc' in self._underlying:
            MessageActivity.resolve_targets(
                self._underlying['cc'],
                object_store,
            )

    @staticmethod
    def resolve_targets(
        targets: Union[str, Iterable[str]],
        object_store: ObjectStore,
    ):
        """Resolves target actors.

        Ignores targets other than an actor.

        :raises requests.HTTPError: if an HTTP request fails.
        """
        if isinstance(targets, str):
            MessageActivity.resolve_target(targets, object_store)
        else:
            for target in targets:
                MessageActivity.resolve_target(target, object_store)

    @staticmethod
    def resolve_target(target_ref: str, object_store: ObjectStore):
        """Resolves a target actor.

        Ignores a target other than an actor.
        Ignores target in ``RESERVED_TARGETS``, too.

        :raises requests.HTTPError: if an HTTP request fails.
        """
        if target_ref in RESERVED_TARGETS:
            return
        target = object_store.get(target_ref)
        if target is None:
            target = DictObject.resolve(target_ref)
            if target.type in ACTOR_TYPES:
                object_store.add(target)
            else:
                LOGGER.debug('ignoring non-actor target: %s', target.type)


class Announce(MessageActivity):
    """Wraps an "Announce" activity.
    """
    @staticmethod
    def parse_object(obj: Dict[str, Any]) -> 'Announce':
        """Parses a given "Announce" activity object.

        :raises ValueError: if ``obj`` does not represent an "Announce"
        activity object.
        """
        if obj.get('type') != 'Announce':
            raise ValueError(f'type must be "Announce": {obj.get("type")}')
        return Announce(obj)

    def resolve_objects(self, object_store: ObjectStore):
        """Resolves the referenced object.
        """
        super().resolve_objects(object_store)
        # resolves the object
        if 'object' in self._underlying:
            obj_ref = Reference(self._underlying['object'])
            obj = object_store.get(obj_ref.id)
            if obj is None:
                obj = DictObject.resolve(obj_ref.ref)
                object_store.add(obj)


class Create(MessageActivity):
    """Wraps a "Create" activity.
    """
    @staticmethod
    def parse_object(obj: Dict[str, Any]) -> 'Create':
        """Parses a given "Create" activity object.

        :raises ValueError: if ``obj`` does not represent a "Create" activity
        object.
        """
        if obj.get('type') != 'Create':
            raise ValueError(f'type must be "Create": {obj.get("type")}')
        return Create(obj)

    def resolve_objects(self, object_store: ObjectStore):
        """Resolves the referenced object.
        """
        super().resolve_objects(object_store)
        # resolves the object
        if 'object' in self._underlying:
            obj_ref = Reference(self._underlying['object'])
            obj = object_store.get(obj_ref.id)
            if obj is None:
                obj = DictObject.resolve(obj_ref.ref)
                object_store.add(obj)
