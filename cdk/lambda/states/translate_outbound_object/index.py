# -*- coding: utf-8 -*-

"""Translates an outbound object in the staging outbox.

You have to specify the following environment variables:
* ``OBJECTS_STORE_NAME``: name of the S3 bucket that stores objects.
* ``USER_TABLE_NAME``: name of the DynamoDB table that stores user information.
* ``DOMAIN_NAME_PARAMETER_PATH``: path to the parameter storing the domain name
  in Parameter Store on AWS Systems Manager.
"""

import logging
import os
import boto3
from libactivitypub.activity import Accept, Activity, Create
from libactivitypub.activity_streams import ACTIVITY_STREAMS_CONTEXT
from libactivitypub.data_objects import Note
from libactivitypub.objects import DictObject
from libmumble.exceptions import BadConfigurationError, NotFoundError
from libmumble.parameters import get_domain_name
from libmumble.objects_store import (
    dict_as_object_key,
    get_username_from_staging_outbox_key,
    load_object,
    save_activity_in_outbox,
    save_post,
)
from libmumble.user_table import User, UserTable
from libmumble.utils import current_yyyymmdd_hhmmss


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
# turns on logs from some dependencies
logging.getLogger('libactivitypub').setLevel(logging.DEBUG)
logging.getLogger('libmumble').setLevel(logging.DEBUG)

DOMAIN_NAME = get_domain_name(boto3.client('ssm'))

OBJECTS_BUCKET_NAME = os.environ['OBJECTS_BUCKET_NAME']
S3_CLIENT = boto3.client('s3')

USER_TABLE_NAME = os.environ['USER_TABLE_NAME']
USER_TABLE = UserTable(boto3.resource('dynamodb').Table(USER_TABLE_NAME))


def translate_object(obj: DictObject, user: User) -> Activity:
    """Translates a given object into the activity to be staged.

    :raises TypeError: if ``obj`` is malformed,
    or if ``obj`` cannot be delivered.
    """
    if obj.type == 'Accept':
        return translate_accept(obj.cast(Accept), user)
    if obj.type == 'Note':
        return translate_note(obj.cast(Note), user)
    raise TypeError(f'underliverable object: {obj.type}')


def translate_accept(accept: Accept, user: User) -> Accept:
    """Translates a given "Accept" activity.

    Assigns the following properties to ``accept``:
    * "@context"
    * "id"
    """
    accept.set_jsonld_context(ACTIVITY_STREAMS_CONTEXT)
    accept.id = user.generate_activity_id()
    return accept


def translate_note(note: Note, user: User) -> Create:
    """Translates a given "Note" object.

    Assigns the following properties to ``note``.
    * "@context"
    * "id" ← random ID
    * "attributedTo" ← ``user.id``
    * "published" ← current time

    And saves it in the object store,
    then wraps it with a "Create" activity.
    """
    note.set_jsonld_context(ACTIVITY_STREAMS_CONTEXT)
    note.id = user.generate_post_id()
    note.attributed_to = user.id
    note.published = current_yyyymmdd_hhmmss()
    save_post(S3_CLIENT, OBJECTS_BUCKET_NAME, note)
    create = Create.wrap_note(note)
    create.id = user.generate_activity_id()
    return create


def lambda_handler(event, _context):
    """Runs on AWS Lambda.

    ``event`` must be a ``dict`` similar to the following:

    .. code-block:: python

        {
            'object': {
                'bucket': '<bucket-name>',
                'key': '<object-key>'
            }
        }
    """
    LOGGER.debug('translating object: %s', event)
    object_key = dict_as_object_key(event['object'])
    if object_key['bucket'] != OBJECTS_BUCKET_NAME:
        raise BadConfigurationError(
            'objects bucket mismatch:'
            ' {OBJECTS_BUCKET_NAME} != {object_key["bucket"]}',
        )
    username = get_username_from_staging_outbox_key(object_key['key'])
    LOGGER.debug('looking up user: %s', username)
    user = USER_TABLE.find_user_by_username(username, DOMAIN_NAME)
    if user is None:
        raise NotFoundError(f'no such user: {username}')
    LOGGER.debug('loading object: %s', object_key)
    obj = load_object(S3_CLIENT, object_key)
    LOGGER.debug('translating object: %s', obj.to_dict())
    activity = translate_object(obj, user)
    LOGGER.debug('staging activity: %s', activity.to_dict())
    save_activity_in_outbox(S3_CLIENT, OBJECTS_BUCKET_NAME, activity)
