# -*- coding: utf-8 -*-

"""Expands recipients of a staged activity in the outbox.

You have to specify the following environment variable:
* ``OBJECTS_BUCKET_NAME``: name of the S3 bucket that stores objects to be
  delivered.
* ``USER_TABLE_NAME``: name of the DynamoDB table that stores user information.
* ``DOMAIN_NAME_PARAMETER_PATH``: path to the parameter storing the domain name
  in Parameter Store on AWS Systems Manager.
"""

import logging
import os
from typing import Iterable, List, Set, Union
from urllib.parse import urlparse
import boto3
from libactivitypub.activity import Accept, Activity, ActivityVisitor, Create
from libactivitypub.activity_streams import ACTIVITY_STREAMS_PUBLIC_ADDRESS
from libactivitypub.actor import Actor
from libactivitypub.data_objects import COLLECTION_TYPES
from libactivitypub.objects import DictObject
from libmumble.parameters import get_domain_name
from libmumble.exceptions import (
    BadConfigurationError,
    NotFoundError,
    TooManyAccessError,
    TransientError,
)
from libmumble.id_scheme import split_user_path
from libmumble.objects_store import (
    dict_as_object_key,
    get_username_from_outbox_key,
    load_activity,
)
from libmumble.user_table import User, UserTable
import requests


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

OBJECTS_BUCKET_NAME = os.environ['OBJECTS_BUCKET_NAME']

USER_TABLE_NAME = os.environ['USER_TABLE_NAME']
USER_TABLE = UserTable(boto3.resource('dynamodb').Table(USER_TABLE_NAME))

# caching domain name should not harm
DOMAIN_NAME = get_domain_name(boto3.client('ssm'))


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

        :raises requests.HTTPError: if an http request to other server fails.

        :raises requests.Timeout if an http request to other server times out.:

        :raises NotFoundError: if an internal user does not exist in this
        server.

        :raises TooManyAccessError: if access to the DynamoDB table exceeds
        the limit.

        :raises ValueError: if an internal path is invalid.
        """
        self._excluded.add(create.actor_id) # excludes the sender
        if hasattr(create, 'to'):
            LOGGER.debug('resolving "to"')
            self.resolve_inboxes(create.to)
        if hasattr(create, 'cc'):
            LOGGER.debug('resolving "cc"')
            self.resolve_inboxes(create.cc)
        if hasattr(create, 'bcc'):
            LOGGER.debug('resolving "bcc"')
            self.resolve_inboxes(create.bcc)

    def visit_accept(self, accept: Accept):
        """Expands recipients of an "Accept" activity.

        :raises requests.HTTPError: if an http request to other server fails.

        :raises requests.Timeout: if an http request to other server times out.

        :raises TypeError: if the accept object is not an activity.

        :raises NotFoundError: if an internal user does not exist in this
        server.

        :raises TooManyAccessError: if access to the DynamoDB table exceeds
        the limit.

        :raises ValueError: if an internal path is invalid.
        """
        self._excluded.add(accept.actor_id) # excludes the sender
        LOGGER.debug('resolving accepted object')
        accepted = accept.resolve_object_activity()
        self.resolve_inboxes_of_recipient(accepted.actor_id)

    def resolve_inboxes(self, recipients: Union[str, Iterable[str]]):
        """Resolves inbox URIs of given recipients.

        :raises requests.HTTPError: if an http request to other server fails.

        :raises requests.Timeout: if an http request to other server times out.

        :raises NotFoundError: if an internal user does not exist in this
        server.

        :raises TooManyAccessError: if access to the DynamoDB table exceeds
        the limit.

        :raises ValueError: if an internal path is invalid.
        """
        if isinstance(recipients, str):
            self.resolve_inboxes_of_recipient(recipients)
        else:
            for recipient in recipients:
                self.resolve_inboxes_of_recipient(recipient)

    def resolve_inboxes_of_recipient(self, recipient: str):
        """Resolves inbox URIs of a single recipient.

        :raises requests.HTTPError: if an http request to other server fails.

        :raises requests.Timeout: if an http request to other server times out.

        :raises NotFoundError: if an internal user does not exist in this
        server.

        :raises TooManyAccessError: if access to the DynamoDB table exceeds
        the limit.

        :raises ValueError: if an internal path is invalid.
        """
        if recipient in self._excluded:
            return
        if recipient in self._collected:
            return
        self._collected.add(recipient)
        LOGGER.debug('resolving recipient: %s', recipient)
        parsed_uri = urlparse(recipient)
        if parsed_uri.hostname == DOMAIN_NAME:
            self.resolve_internal_inboxes(parsed_uri.path)
            return
        try:
            obj = DictObject.resolve(recipient)
        except requests.HTTPError as exc:
            if exc.response.status_code == 410:
                LOGGER.warning('recipient is gone: %s', recipient)
                # TODO: issue an event to delete the recipient
                return
            raise
        if obj.type == 'Person':
            actor = obj.cast(Actor)
            if actor.shared_inbox is not None:
                LOGGER.debug(
                    'recipient has a shared inbox: %s',
                    actor.shared_inbox.uri,
                )
                self.recipients.add(actor.shared_inbox.uri)
            else:
                self.recipients.add(actor.inbox.uri)
        elif obj.type in COLLECTION_TYPES:
            LOGGER.debug('resolving recipient collection: %s', recipient)
            # TODO: resolve the collection
        else:
            raise TypeError(
                'unsupported recipient type "{obj.type}": {recipient}',
            )

    def resolve_internal_inboxes(self, path_part: str):
        """Resolves inbox URIs of a single recipient resides in this server.

        The recipient may be
        * a user resides in this server

        :raises requests.HTTPError: if an HTTP request to other server fails.

        :raises requests.Timeout: if an HTTP request to other server times out.

        :raises ValueError: if ``path_part`` is not associated with a user,
        or if ``path_part`` does not represent followers.

        :raises NotFoundError: if an internal user does not exist in this
        server.

        :raises TooManyAccessError: if access to the DynamoDB table exceeds
        the limit.
        """
        LOGGER.debug('resolving internal inboxes: %s', path_part)
        username, remaining = split_user_path(path_part)
        user = USER_TABLE.find_user_by_username(username, DOMAIN_NAME)
        if user is None:
            raise NotFoundError(f'no such user: {username}')
        if remaining == '':
            LOGGER.debug('internal user: %s', username)
            self.recipients.add(user.inbox_uri)
        elif remaining == '/followers':
            LOGGER.debug('expanding user followers: %s', username)
            self.resolve_user_followers(user)
        else:
            raise ValueError(f'unresolvable internal entity: {path_part}')

    def resolve_user_followers(self, user: User):
        """Resolves inbox URIs of the followers of a given user.

        :raises TooManyAccessError: if access to the DynamoDB table exceeds
        the limit.
        """
        items_per_query = 100
        for follower_id in user.enumerate_followers(items_per_query):
            self.resolve_inboxes_of_recipient(follower_id)


def expand_recipients(activity: Activity) -> List[str]:
    """Expands recipients of a given activity.

    :returns: list of inbox URIs of the recipients of ``activity``.

    :raises TransientError: if an http request to other server fails with
    a transient error; e.g., timeout, 429 status code.

    :raises requests.HTTPError: if an http request to other server fails with
    a non-transient error.
    """
    try:
        visitor = RecipientCollector()
        activity.visit(visitor)
        return list(visitor.recipients)
    except TooManyAccessError as exc:
        raise TooManyAccessError(f'{exc}') from exc
    except requests.HTTPError as exc:
        if exc.response.status_code == 429:
            raise TransientError(f'too many HTTP requests: {exc}') from exc
        raise
    except requests.Timeout as exc:
        raise TransientError(f'HTTP request timed out: {exc}') from exc


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
            'recipients': [
                '<inbox-uri>',
            ]
        }

    :raises BadConfigurationError: if ``activity.bucket`` does not match the
    configured objects bucket, if ``activity.key`` is not in the staging
    outbox.

    :raises NotFoundError: if the owner of the activity object is not found.

    :raises TransientError: if an http request to other server fails with
    a transient error; e.g., timeout, 429 status code,
    or if access to the DynamoDB table exceeds the limit.

    :raises requests.HTTPError: if an http request to other server fails with
    a non-transient error.

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
        username = get_username_from_outbox_key(object_key['key'])
    except ValueError as exc:
        raise BadConfigurationError(f'{exc}') from exc
    LOGGER.debug('looking up user: %s', username)
    user = USER_TABLE.find_user_by_username(username, DOMAIN_NAME)
    if user is None:
        raise NotFoundError(f'no such user: {username}')
    LOGGER.debug('loading object: %s', object_key)
    activity = load_activity(boto3.client('s3'), object_key)
    LOGGER.debug('expanding recipients: %s', activity.to_dict())
    recipients = expand_recipients(activity)
    return {
        'recipients': recipients,
    }
