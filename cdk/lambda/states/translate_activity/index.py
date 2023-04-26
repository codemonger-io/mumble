# -*- coding: utf-8 -*-

"""Translates an activity.

This function is intended to be a step on a state machine.

You have to specify the following environment variable:
* ``OBJECTS_BUCKET_NAME``: name of the S3 bucket that stores activity objects.
* ``USER_TABLE_NAME``: name of the DynamoDB table that stores user information.
"""

import json
import logging
import os
from typing import Any, Optional, TypedDict
import boto3
from libactivitypub.activity import (
    Accept,
    Activity,
    ActivityVisitor,
    Follow,
    ResponseActivity,
    Undo,
)
from libmumble.exceptions import (
    BadConfigurationError,
    CommunicationError,
    CorruptedDataError,
    NotFoundError,
    TransientError,
)
from libmumble.objects_store import get_username_from_inbox_key
from libmumble.user_table import UserTable
import requests


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
# turns on logs from some dependencies
logging.getLogger('libactivitypub').setLevel(logging.DEBUG)
logging.getLogger('libmumble').setLevel(logging.DEBUG)

OBJECTS_BUCKET_NAME = os.environ['OBJECTS_BUCKET_NAME']

USER_TABLE_NAME = os.environ['USER_TABLE_NAME']
USER_TABLE = UserTable(boto3.resource('dynamodb').Table(USER_TABLE_NAME))


class StoredActivity(TypedDict):
    """Activity stored in an S3 bucket.
    """
    bucket: str
    """Bucket name."""
    key: str
    """Object key."""


def dict_as_stored_activity(d: Any) -> StoredActivity: # pylint: disable=invalid-name
    """Casts a given ``dict`` as a ``StoredActivity``.

    :raises TypeError: if ``d`` is not a ``StoredActivity``.

    :raises KeyError: if ``d`` is missing a necessary key.
    """
    if not isinstance(d, dict):
        raise TypeError(f'dict is expected but: {type(d)}')
    if not isinstance(d['bucket'], str):
        raise TypeError(f'bucket must be str but: {type(d["bucket"])}')
    if not isinstance(d['key'], str):
        raise TypeError(f'key must be str but: {type(d["key"])}')
    # unfortunately, above checks cannot convince d is StoredActivity
    return d # type: ignore


class ActivityTranslator(ActivityVisitor):
    """``ActivityVistor`` that translates an activity.
    """
    username: str
    """Username of the inbox owner."""
    response: Optional[ResponseActivity]=None
    """Optional response to the translated activity.
    ``None`` if there is no response.
    """

    def __init__(self, username: str):
        """Initializes with the username of the inbox owner.
        """
        self.username = username

    def visit_follow(self, follow: Follow):
        """Translates a "Follow" activity.

        Responds with "Accept".

        :raises ValueError: if the object of the activity is not the inbox
        owner.

        :raises TooManyAccessError: if there are too many requests.
        """
        LOGGER.debug('translating Follow: %s', follow.to_dict())
        USER_TABLE.add_user_follower(self.username, follow)
        self.response = Accept.create(
            actor_id=follow.followed_id,
            activity=follow,
        )

    def visit_undo(self, undo: Undo):
        """Translates an "Undo" activity.

        :raises ValueError: if the undone object has a problem.

        :raises TypeError: if the undone object has a type error.

        :raises requests.HTTPError: if an HTTP request fails.

        :raises requests.Timeout: if an HTTP request times out.

        :raises TooManyAccessError: if there are too many requests.
        """
        LOGGER.debug('translating Undo: %s', undo.to_dict())
        undoer = Undoer(self.username)
        activity = undo.resolve_undone_activity()
        activity.visit(undoer)


class Undoer(ActivityVisitor):
    """``ActivityVisitor`` that undoes an activity.
    """
    username: str
    """Username of the inbox owner."""

    def __init__(self, username: str):
        """Initializes with the username of the inbox owner.
        """
        self.username = username

    def visit_follow(self, follow: Follow):
        """Undoes a "Follow" activity.

        :raises ValueError: if the unfollowed user is not the inbox owner.

        :raises TooManyAccessError: if there are too many requests.
        """
        LOGGER.debug('undoing Follow: %s', follow.to_dict())
        USER_TABLE.remove_user_follower(self.username, follow)


def load_activity(stored_activity: StoredActivity) -> Activity:
    """Loads an activity stored in an S3 bucket.

    :raises NotFoundError: if the specified object is not found.

    :raises CorruptedDataError: if the specified object does not represent
    a valid activity.
    """
    s3_client = boto3.client('s3')
    try:
        res = s3_client.get_object(
            Bucket=stored_activity['bucket'],
            Key=stored_activity['key'],
        )
    except s3_client.exceptions.NoSuchKey as exc:
        raise NotFoundError(
            f'no such activity object: {stored_activity}',
        ) from exc

    body = res['Body']
    try:
        data = body.read()
    finally:
        body.close()

    try:
        return Activity.parse_object(json.loads(data))
    except (TypeError, ValueError) as exc:
        raise CorruptedDataError(f'{exc}') from exc


def translate_activity(
    activity: Activity,
    username: str,
) -> Optional[ResponseActivity]:
    """Translates a given activity.

    :returns: optional response activity.

    :raises CorruptedDataError: if the activity has an error.

    :raises TooManyAccessError: if there are too many requests.

    :raises TransientError: if the other server fails with a transient error;
    e.g, timeout, 429 status code.

    :raises CommunicationError: if the other server fails with a non-transient
    error.
    """
    try:
        visitor = ActivityTranslator(username)
        activity.visit(visitor)
        return visitor.response
    except (TypeError, ValueError) as exc:
        raise CorruptedDataError(f'{exc}') from exc
    except requests.HTTPError as exc:
        if exc.response.status_code == 429:
            raise TransientError(f'too many requests: {exc}') from exc
        raise CommunicationError(f'{exc}') from exc
    except requests.Timeout as exc:
        raise TransientError(f'request timed out: {exc}') from exc


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
            'response': {
                ...
            }
        }

    ``response`` is optional response activity which may be "Accept".

    :raises BadConfigurationError: ``activity`` does not represents a stored
    activity, or if ``activity.bucket`` does not match ``OBJECTS_BUCKET_NAME``,
    or if ``activity.key`` does not contain the username.

    :raises CorruptedDateError: if the activity object is malformed.

    :raises TooManyAccessError: if there are too many requests.

    :raises NotFoundError: if the activity object is not found.
    """
    try:
        stored_activity = dict_as_stored_activity(event['activity'])
    except (KeyError, TypeError) as exc:
        raise BadConfigurationError(f'{exc}: {event.get("activity")}') from exc

    LOGGER.debug('loading activity: %s', stored_activity)
    if stored_activity['bucket'] != OBJECTS_BUCKET_NAME:
        raise BadConfigurationError(
            'objects bucket mismatch:'
            f' expected={OBJECTS_BUCKET_NAME},'
            f' given={stored_activity["bucket"]}'
        )

    try:
        username = get_username_from_inbox_key(stored_activity['key'])
    except ValueError as exc:
        raise BadConfigurationError(
            f'no username in object key: {exc}',
        ) from exc

    activity = load_activity(stored_activity)

    LOGGER.debug('translating activity: %s', activity.to_dict())
    response = translate_activity(activity, username)

    if response is not None:
        return {
            'response': response.to_dict(),
        }
    return {}
