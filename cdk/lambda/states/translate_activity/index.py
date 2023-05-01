# -*- coding: utf-8 -*-

"""Dispatches an activity received in the inbox.

This function is intended to be a step on a state machine.

You have to specify the following environment variable:
* ``OBJECTS_BUCKET_NAME``: name of the S3 bucket that stores activity objects.
* ``USER_TABLE_NAME``: name of the DynamoDB table that stores user information.
* ``DOMAIN_NAME_PARAMETER_PATH``: path to the parameter containing the domain
  name in Parameter Store on AWS Systems Manager.
"""

import logging
import os
from typing import Optional
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
    NotFoundError,
    TransientError,
)
from libmumble.objects_store import (
    dict_as_object_key,
    get_username_from_inbox_key,
    load_activity,
    save_object,
)
from libmumble.parameters import get_domain_name
from libmumble.user_table import User, UserTable
import requests


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
# turns on logs from some dependencies
logging.getLogger('libactivitypub').setLevel(logging.DEBUG)
logging.getLogger('libmumble').setLevel(logging.DEBUG)

OBJECTS_BUCKET_NAME = os.environ['OBJECTS_BUCKET_NAME']

USER_TABLE_NAME = os.environ['USER_TABLE_NAME']
USER_TABLE = UserTable(boto3.resource('dynamodb').Table(USER_TABLE_NAME))

DOMAIN_NAME = get_domain_name(boto3.client('ssm'))


class ActivityDispatcher(ActivityVisitor):
    """``ActivityVistor`` that dispatches an activity.
    """
    user: User
    """Inbox owner user."""
    response: Optional[ResponseActivity]=None
    """Optional response to the translated activity.
    ``None`` if there is no response.
    """

    def __init__(self, user: User):
        """Initializes with an inbox owner user.
        """
        self.user = user

    def visit_follow(self, follow: Follow):
        """Translates a "Follow" activity.

        Responds with "Accept".

        :raises ValueError: if the object of the activity is not the inbox
        owner.

        :raises TooManyAccessError: if there are too many requests.
        """
        LOGGER.debug('dispatching Follow: %s', follow.to_dict())
        USER_TABLE.add_user_follower(self.user.username, follow)
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
        LOGGER.debug('dispatching Undo: %s', undo.to_dict())
        undoer = Undoer(self.user)
        activity = undo.resolve_undone_activity()
        activity.visit(undoer)


class Undoer(ActivityVisitor):
    """``ActivityVisitor`` that undoes an activity.
    """
    user: User
    """Username of the inbox owner."""

    def __init__(self, user: User):
        """Initializes with the inbox owner user.
        """
        self.user = user

    def visit_follow(self, follow: Follow):
        """Undoes a "Follow" activity.

        :raises ValueError: if the unfollowed user is not the inbox owner.

        :raises TooManyAccessError: if there are too many requests.
        """
        LOGGER.debug('undoing Follow: %s', follow.to_dict())
        USER_TABLE.remove_user_follower(self.user.username, follow)


def dispatch_activity(activity: Activity, user: User):
    """Dispatches a given activity.

    :raises TooManyAccessError: if there are too many requests.

    :raises TransientError: if an http request fails with a transient error;
    e.g, timeout, 429 status code.

    :raises requests.HTTPError: if an http request fails with a non-transient
    error.
    """
    try:
        visitor = ActivityDispatcher(user)
        activity.visit(visitor)
        if visitor.response is not None:
            save_object(
                boto3.client('s3'),
                {
                    'bucket': OBJECTS_BUCKET_NAME,
                    'key': user.generate_staging_outbox_key(),
                },
                visitor.response,
            )
    except requests.HTTPError as exc:
        if exc.response.status_code == 429:
            raise TransientError(f'too many requests: {exc}') from exc
        raise
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

    :raises BadConfigurationError: if ``activity.bucket`` does not match
    ``OBJECTS_BUCKET_NAME``.

    :raises NotFoundError: if the owner of the inbox is not found.

    :raises TooManyAccessError: if there are too many requests.

    :raises TransientError: if an http request to other server fails with
    a transient error; e.g., timeout, 429 status code.

    :raises requests.HTTPError: if an http request to other server fails with
    non-transient error.

    :raises KeyError: if ``event`` is malformed.

    :raises ValueError: if ``event`` is malformed.

    :raises TypeError: if ``event`` is malformed.
    """
    object_key = dict_as_object_key(event['activity'])
    if object_key['bucket'] != OBJECTS_BUCKET_NAME:
        raise BadConfigurationError(
            'objects bucket mismatch:'
            f' {OBJECTS_BUCKET_NAME} vs {object_key["bucket"]}',
        )
    username = get_username_from_inbox_key(object_key['key'])
    LOGGER.debug('looking up user: %s', username)
    user = USER_TABLE.find_user_by_username(username, DOMAIN_NAME)
    if user is None:
        raise NotFoundError(f'no such user: {username}')
    LOGGER.debug('loading activity: %s', object_key)
    activity = load_activity(boto3.client('s3'), object_key)
    LOGGER.debug('dispatching activity: %s', activity.to_dict())
    dispatch_activity(activity, user)
