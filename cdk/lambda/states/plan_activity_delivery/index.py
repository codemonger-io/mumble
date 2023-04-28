# -*- coding: utf-8 -*-

"""Plans delivery of a staged activity.

You have to specify the following environment variable:
* ``OBJECTS_BUCKET_NAME``: name of the S3 bucket that stores objects to be
  delivered.
* ``DOMAIN_NAME_PARAMETER_PATH``: path to the parameter storing the domain name
  in Parameter Store on AWS Systems Manager.
"""

import logging
import os
from typing import Iterable, List, Set, Union
from urllib.parse import urlparse
import boto3
from libactivitypub.activity import Activity, ActivityVisitor, Create
from libactivitypub.activity_streams import (
    ACTIVITY_STREAMS_CONTEXT,
    ACTIVITY_STREAMS_PUBLIC_ADDRESS,
)
from libactivitypub.actor import Actor
from libactivitypub.data_objects import COLLECTION_TYPES, Note
from libactivitypub.objects import DictObject, generate_id
from libmumble.parameters import get_domain_name
from libmumble.exceptions import BadConfigurationError
from libmumble.objects_store import (
    dict_as_object_key,
    get_username_from_staging_outbox_key,
    load_object,
)
from libmumble.utils import current_yyyymmdd_hhmmss


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

OBJECTS_BUCKET_NAME = os.environ['OBJECTS_BUCKET_NAME']

# caching domain name should not harm
DOMAIN_NAME = get_domain_name(boto3.client('ssm'))


def translate_object(obj: DictObject, username: str) -> Activity:
    """Translates a given object and returns an activity to be delivered.

    :raises ValueError: if ``obj`` cannot be delivered, or if ``obj`` has
    invalid value.

    :raises TypeError: if ``obj`` has a type error.
    """
    if obj.type == 'Note':
        return translate_note(obj.cast(Note), username)
    raise ValueError(f'undeliverable object: {obj.type}')


def translate_note(note: Note, username: str) -> Create:
    """Translates a given "Note" object and returns a "Create" activity.

    Adds the following properties to ``note``:
    * "@context"
    * "id"
    * "attributedTo"
    * "published"
    """
    unique_id = generate_id()
    note.set_jsonld_context(ACTIVITY_STREAMS_CONTEXT)
    note.id = f'https://{DOMAIN_NAME}/users/{username}/posts/{unique_id}'
    note.attributed_to = f'https://{DOMAIN_NAME}/users/{username}'
    note.published = current_yyyymmdd_hhmmss()
    create = Create.wrap_note(note)
    create.id = f'https://{DOMAIN_NAME}/users/{username}/activities/{unique_id}'
    return create


class RecipientCollector(ActivityVisitor):
    """``ActivityVisitor`` that collects recipients of an activity.
    """
    recipients: Set[str] = set()
    """Collected recipients' inbox URIs."""
    # excluded entity IDs
    _excluded: Set[str] = set([ACTIVITY_STREAMS_PUBLIC_ADDRESS])
    # collected entity IDs
    _collected: Set[str] = set()

    def visit_create(self, create: Create):
        """Expands recipients of a "Create" activity.
        """
        self._excluded.add(create.actor_id) # excludes the sender
        if hasattr(create, 'to'):
            self.resolve_inboxes(create.to)
        if hasattr(create, 'cc'):
            self.resolve_inboxes(create.cc)
        if hasattr(create, 'bcc'):
            self.resolve_inboxes(create.bcc)

    def resolve_inboxes(self, recipients: Union[str, Iterable[str]]):
        """Resolves inbox URIs of given recipients.
        """
        if isinstance(recipients, str):
            self.resolve_inboxes_of_recipient(recipients)
        else:
            for recipient in recipients:
                self.resolve_inboxes_of_recipient(recipient)

    def resolve_inboxes_of_recipient(self, recipient: str):
        """Resolves inbox URIs of a single recipients.
        """
        if recipient in self._excluded:
            return
        if recipient in self._collected:
            return
        self._collected.add(recipient)
        LOGGER.debug('resolving recipient: %s', recipient)
        parsed_uri = urlparse(recipient)
        if parsed_uri.hostname == DOMAIN_NAME:
            self.resolve_internal_inboxes(recipient, parsed_uri.path)
            return
        obj = DictObject.resolve(recipient)
        if obj.type == 'Person':
            actor = obj.cast(Actor)
            self.recipients.add(actor.inbox.uri)
        elif obj.type in COLLECTION_TYPES:
            LOGGER.debug('resolving recipient collection: %s', recipient)
            # TODO: resolve the collection
        else:
            raise TypeError(
                'unsupported recipient type "{obj.type}": {recipient}',
            )

    def resolve_internal_inboxes(self, recipient: str, path_part: str):
        """Resolves inbox URIs of a single recipient resides in this server.
        """
        LOGGER.debug('resolving internal inboxes: %s', path_part)
        # TODO: resolve the internal inboxes


def expand_recipients(activity: Activity) -> List[str]:
    """Expands recipients of a given activity.

    :returns: list of inbox URIs of the recipients of ``activity``.
    """
    visitor = RecipientCollector()
    activity.visit(visitor)
    return list(visitor.recipients)


def lambda_handler(event, _context):
    """Runs on AWS Lambda.

    ``event`` must be a ``dict`` similar to the following:

    .. code-block:: python

        {
            'activity': {
                'bucket': '<bucket-name>',
                'key': '<object-key>'
            }
        }

    Returns a ``dict`` similar to the following:

    .. code-block:: python

        {
            'activity': {},
            'recipients': [
                '<inbox-uri>',
            ]
        }

    :raises BadConfigurationError: if ``activity.bucket`` does not match the
    configured objects bucket, if ``activity.key`` is not in the staging
    outbox.

    :raises ValueError: if the loaded data is invalid.

    :raises TypeError: if the loaded data is incompatible.
    """
    LOGGER.debug('planning activity delivery: %s', event)
    object_key = dict_as_object_key(event['activity'])
    if object_key['bucket'] != OBJECTS_BUCKET_NAME:
        raise BadConfigurationError(
            'objects bucket mismatch:'
            f' {OBJECTS_BUCKET_NAME} vs {object_key["bucket"]}',
        )
    try:
        username = get_username_from_staging_outbox_key(object_key['key'])
    except ValueError as exc:
        raise BadConfigurationError(f'{exc}') from exc
    LOGGER.debug('loading object: %s', object_key)
    obj = load_object(boto3.client('s3'), object_key)
    LOGGER.debug('translating object: %s', obj.to_dict())
    activity = translate_object(obj, username)
    LOGGER.debug('expanding recipients: %s', activity.to_dict())
    recipients = expand_recipients(activity)
    return {
        'activity': activity.to_dict(),
        'recipients': recipients,
    }
