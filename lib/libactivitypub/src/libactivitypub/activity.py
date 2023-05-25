# -*- coding: utf-8 -*-

"""Provides access to activities.
"""

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, Iterable, Optional, Union
import requests
from .activity_streams import (
    ACTIVITY_STREAMS_CONTEXT,
    get as activity_streams_get,
)
from .data_objects import Note
from .objects import (
    ACTOR_TYPES,
    APObject,
    DictObject,
    Link,
    Reference,
    ObjectStore,
)


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

        :raises ValueError: if ``underlying`` does not represent a valid
        object, or if ``underlying`` has no ``actor``.
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
        if obj_type == 'Follow':
            return Follow.parse_object(obj)
        if obj_type == 'Like':
            return Like(obj)
        if obj_type == 'Undo':
            return Undo.parse_object(obj)
        if obj_type == 'Accept':
            return Accept(obj)
        if obj_type == 'Reject':
            return Reject(obj)
        if obj_type is not None:
            raise ValueError(f'unsupported activity type: {obj_type}')
        raise ValueError('invalid object: type is missing')

    @property
    def actor_id(self) -> str:
        """ID of the actor of this activity.
        """
        return Reference(self._underlying['actor']).id

    def is_deliverable(self) -> bool:
        """Returns if this activity has minimum properties that make it
        deliverable.

        An activity is deliverable if it has all of the following properties:
        * "@context"
        * "id"
        * "type"
        """
        required_props = ['@context', 'id', 'type']
        return all((p in self._underlying for p in required_props))

    @abstractmethod
    def visit(self, visitor: 'ActivityVisitor'):
        """Visits this activity.

        You can safely casts this activity to a specific type by using this
        method.
        """

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


# TODO: this class is almost meaningless, because `to`, `cc`, and `bcc` are
#       now included in ``DictObject``.
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
        but an unauthorized (401) error is ignored with a warning message.
        """
        if isinstance(targets, str):
            MessageActivity.resolve_target(targets, object_store)
        else:
            for target in targets:
                try:
                    MessageActivity.resolve_target(target, object_store)
                except requests.HTTPError as exc:
                    # ignores an unauthorized target
                    if exc.response.status_code == 401:
                        LOGGER.warning(
                            'unauthorized access to target: %s',
                            target,
                        )
                    else:
                        raise exc

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

    def visit(self, visitor: 'ActivityVisitor'):
        visitor.visit_announce(self)

    def resolve_objects(self, object_store: ObjectStore):
        """Resolves the referenced object.

        Resolves ``object``.
        """
        super().resolve_objects(object_store)
        # resolves the object
        if 'object' in self._underlying:
            resolve_object(self._underlying['object'], object_store)


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

    @staticmethod
    def wrap_note(note: Note) -> 'Create':
        """Wraps a given "Note" object.

        Copies properties from ``note``:
        * "to" (optional)
        * "cc" (optional)
        * "bcc" (optional)
        * "published"
        * "attributedTo" → "actor"

        Sets a copy of ``note`` to "object".

        Leaves "id" blank.

        :raises AttributeError: if ``note`` does not have "attributedTo",
        or if ``note`` does not have "published".
        """
        obj = {
            '@context': ACTIVITY_STREAMS_CONTEXT,
            'type': 'Create',
            "actor": note.attributed_to,
            "published": note.published,
            "object": note.to_dict(with_context=False),
        }
        options = ['to', 'cc', 'bcc']
        for option in options:
            if hasattr(note, option):
                obj[option] = getattr(note, option)
        return Create(obj)

    @property
    def object(self) -> Reference:
        """Reference to the created object.
        """
        return Reference(self._underlying['object'])

    @object.setter
    def object(self, obj: Reference):
        """Replaces the created object.
        """
        self._underlying['object'] = obj.ref

    def visit(self, visitor: 'ActivityVisitor'):
        visitor.visit_create(self)

    def resolve_objects(self, object_store: ObjectStore):
        """Resolves the referenced object.

        Resolves ``object``.
        """
        super().resolve_objects(object_store)
        if 'object' in self._underlying:
            resolve_object(self._underlying['object'], object_store)


class Follow(Activity):
    """Wraps a "Follow" activity.
    """
    def __init__(self, underlying: Dict[str, Any]):
        """Wraps a given "Follow" activity object.

        :raises ValueError: if ``underlying`` does not represent an activity,
        or if ``underlying`` does not have ``object``.
        """
        super().__init__(underlying)
        if 'object' not in underlying:
            raise ValueError('invalid follow activity: object is missing')

    @staticmethod
    def parse_object(obj: Dict[str, Any]) -> 'Follow':
        """Parses a given "Follow" activity object.

        :raises ValueError: if ``obj`` does not represent a "Follow" activity
        object.
        """
        if obj.get('type') != 'Follow':
            raise ValueError(f'type must be "Follow": {obj.get("type")}')
        return Follow(obj)

    def visit(self, visitor: 'ActivityVisitor'):
        visitor.visit_follow(self)

    def resolve_objects(self, object_store: ObjectStore):
        """Resolves the referenced object.

        Resolves ``object``.
        """
        super().resolve_objects(object_store)
        resolve_object(self._underlying['object'], object_store)

    @property
    def followed_id(self):
        """ID of the followed object.
        """
        return Reference(self._underlying['object']).id


class Like(Activity):
    """Wraps a "Like" activity.
    """
    def __init__(self, underlying: Dict[str, Any]):
        """Wraps a given "Like" activity object.

        :raises ValueError: if ``underlying`` does not represent an activity,
        or if ``underlying`` does not have ``object``.
        """
        super().__init__(underlying)
        if 'object' not in underlying:
            raise ValueError('invalid like activity: object is missing')

    def visit(self, visitor: 'ActivityVisitor'):
        visitor.visit_like(self)

    def resolve_objects(self, object_store: ObjectStore):
        """Resolves the referenced object.

        Resolves ``object``.
        """
        super().resolve_objects(object_store)
        resolve_object(self._underlying['object'], object_store)


class Undo(Activity):
    """Wraps an "Undo" activity.
    """
    def __init__(self, underlying: Dict[str, Any]):
        """Wraps a given "Undo" activity object.

        :raises ValueError: if ``underlying`` does not represent an activity,
        or if ``underlying`` does not have ``object``.
        """
        super().__init__(underlying)
        if 'object' not in underlying:
            raise ValueError('invalid undo activity: object is missing')

    @staticmethod
    def parse_object(obj: Dict[str, Any]) -> 'Undo':
        """Parses a given "Undo" activity object.

        :raises ValueError: if ``obj`` does not represent an "Undo" activity
        object.
        """
        if obj.get('type') != 'Undo':
            raise ValueError(f'type must be "Undo": {obj.get("type")}')
        return Undo(obj)

    def visit(self, visitor: 'ActivityVisitor'):
        visitor.visit_undo(self)

    def resolve_objects(self, object_store: ObjectStore):
        """Resolves the referenced object.

        Resolves ``object``.
        """
        super().resolve_objects(object_store)
        resolve_object(self._underlying['object'], object_store)

    def resolve_undone_activity(self) -> Activity:
        """Resolves the undone activity.

        :raises requests.HTTPError: if an HTTP request fails.

        :raises requests.Timeout: if an HTTP request times out.

        :raises ValueError: if a resolved data does not represent an activity.

        :raises TypeError: if a resolved data contains an incompatible type.
        """
        return resolve_activity(self._underlying['object'])

    @property
    def undone_id(self):
        """ID of the undone object.
        """
        return Reference(self._underlying['object']).id


class ResponseActivity(Activity):
    """Activity sent as a response.

    There are "Accept" and "Reject" so far.
    """
    def __init__(self, underlying: Dict[str, Any]):
        """Wraps a given response activity object.

        :raises ValueError: if ``underlying`` does not represent an activity,
        or if ``underlying`` does not have ``object``.
        """
        super().__init__(underlying)
        if 'object' not in underlying:
            raise ValueError('invalid response activity: object is missing')

    def resolve_objects(self, object_store: ObjectStore):
        """Resolves the reference object.

        Resolves ``object``.
        """
        super().resolve_objects(object_store)
        resolve_object(self._underlying['object'], object_store)

    @property
    def object_id(self) -> str:
        """ID of the object.
        """
        return Reference(self._underlying['object']).id

    def resolve_object_activity(self) -> Activity:
        """Resolves the object of this activity.

        :raises requests.HTTPError: if an HTTP request fails.

        :raises requests.Timeout: if an HTTP request times out.

        :raises TypeError: if the resolved object is not an activity.
        """
        return resolve_activity(self._underlying['object'])


class Accept(ResponseActivity):
    """Wraps an "Accept" activity.
    """
    def __init__(self, underlying: Dict[str, Any]):
        """Wraps a given "Accept" activity object.

        :raises ValueError: if ``underlying`` does not represent an "Accept"
        activity object.

        :raises TypeError: if ``underlying`` contains an incompatible type.
        """
        super().__init__(underlying)
        if self.type != 'Accept':
            raise ValueError(f'type must be "Accept": {self.type}')

    @staticmethod
    def create(actor_id: str, activity: Activity) -> 'Accept':
        """Creates an "Accept" from a given actor to another actor regarding
        a given activity.
        """
        return Accept({
            'type': 'Accept',
            'actor': actor_id,
            'object': activity.to_dict(with_context=False),
        })

    def visit(self, visitor: 'ActivityVisitor'):
        visitor.visit_accept(self)


class Reject(ResponseActivity):
    """Wraps an "Reject" activity.
    """
    def __init__(self, underlying: Dict[str, Any]):
        """Wraps a given "Reject" activity object.

        :raises ValueError: if ``underlying`` does not represent a "Reject"
        activity object.

        :raises TypeError: if ``underlying`` contains an incompatible type.
        """
        super().__init__(underlying)
        if self.type != 'Reject':
            raise ValueError(f'type must be "Reject": {self.type}')

    def visit(self, visitor: 'ActivityVisitor'):
        visitor.visit_reject(self)


class ActivityVisitor(ABC):
    """Visitor that processes typed activities.

    You have to override visitor methods specific to your needs.
    Visitor methods do nothing by default.
    """
    def visit_announce(self, announce: Announce):
        """Processes an "Announce" activity.
        """
        LOGGER.debug('ignoring "Announce": %s', announce._underlying) # pylint: disable=protected-access

    def visit_create(self, create: Create):
        """Processes a "Create" activity.
        """
        LOGGER.debug('ignoring "Create": %s', create._underlying) # pylint: disable=protected-access

    def visit_follow(self, follow: Follow):
        """Processes a "Follow" activity.
        """
        LOGGER.debug('ignoring "Follow": %s', follow._underlying) # pylint: disable=protected-access

    def visit_like(self, like: Like):
        """Processes a "Like" activity.
        """
        LOGGER.debug('ignoring "Like": %s', like._underlying) # pylint: disable=protected-access

    def visit_undo(self, undo: Undo):
        """Processes an "Undo" activity.
        """
        LOGGER.debug('ignoring "Undo": %s', undo._underlying) # pylint: disable=protected-access

    def visit_accept(self, accept: Accept):
        """Processes an "Accept" activity.
        """
        LOGGER.debug('ignoring "Accept": %s', accept._underlying) # pylint: disable=protected-access

    def visit_reject(self, reject: Reject):
        """Processes a "Reject" activity.
        """
        LOGGER.debug('ignoring "Reject": %s', reject._underlying) # pylint: disable=protected-access


def resolve_object(
    maybe_obj: Union[str, Dict[str, Any]],
    object_store: ObjectStore,
) -> Optional[APObject]:
    """Resolves an object and stores in an ``ObjectStore``.

    ``maybe_obj`` may be a URI, a link object, or a ``dict`` representation of
    the object itself.

    Returns the object in ``object_store`` if there is one associated with the
    object ID.

    Returns ``None`` if access to the object is unauthorized.

    :raises requests.HTTPError: if an HTTP request fails.
    but an unauthorized (401) error is ignored with a warning message.

    :raises requests.Timeout: if an HTTP request times out.

    :raises ValueError: if the object data is invalid.

    :raises TypeError: if the object data contains an incompatible type.
    """
    obj_ref = Reference(maybe_obj)
    obj = object_store.get(obj_ref.id)
    if obj is None:
        try:
            obj = DictObject.resolve(obj_ref.ref)
        except requests.HTTPError as exc:
            # ignores an unauthorized object with a warning
            if exc.response.status_code == 401:
                LOGGER.warning('unauthorized object: %s', obj_ref.ref)
            else:
                raise exc
        else:
            object_store.add(obj)
    return obj


def resolve_activity(maybe_obj: Union[str, Dict[str, Any]]) -> Activity:
    """Resolves an activity.

    ``maybe_obj`` may be a URI, a link object, or a ``dict`` representation of
    the activity itself.

    :raises requests.HTTPError: if an HTTP request fails.

    :raises requests.Timeout: if an HTTP request times out.

    :raises ValueError: if the activity data is invalid.

    :raises TypeError: if the activity data contains an incompatible type.
    """
    if isinstance(maybe_obj, str):
        LOGGER.debug('requesting: %s', maybe_obj)
        obj = activity_streams_get(maybe_obj)
    elif maybe_obj.get('type') == 'Link':
        link = Link(maybe_obj)
        LOGGER.debug('requesting: %s', link.href)
        obj = activity_streams_get(link.href)
    else:
        obj = maybe_obj
    return Activity.parse_object(obj)
