# -*- coding: utf-8 -*-

"""Provides utilities around the objects store.
"""

import json
import logging
import re
from typing import Any, Dict, TypedDict
from libactivitypub.activity import Activity
from libactivitypub.data_objects import Note
from libactivitypub.objects import DictObject
from .exceptions import NotFoundError
from .id_scheme import (
    parse_user_activity_id,
    parse_user_post_id,
)


LOGGER = logging.getLogger('libmumble.objects_store')
LOGGER.setLevel(logging.DEBUG)


class ObjectKey(TypedDict):
    """``dict`` representation of an object key in an S3 bucket.
    """
    bucket: str
    """Name of the S3 bucket."""
    key: str
    """Key of the object."""


def dict_as_object_key(d: Dict[str, Any]) -> ObjectKey: # pylint: disable=invalid-name
    """Casts a given ``dict`` as an ``ObjectKey``.

    :raises TypeError: if ``d`` is incompatible with ``ObjectKey``.
    """
    if not isinstance(d.get('bucket'), str):
        raise TypeError(f'"bucket" must be str but ${type(d.get("bucket"))}')
    if not isinstance(d.get('key'), str):
        raise TypeError(f'"key" must be str but ${type(d.get("key"))}')
    # unfortunately, above checks cannot convince d is ObjectKey
    return d # type: ignore


def get_username_from_key(prefix: str, key: str) -> str:
    """Extracts the username from a given object key.

    :param str prefix: prefix of the key. any characters reserved by regex
    must be properyly escaped.
    """
    pattern = f'^{prefix}\\/users\\/([^/]+)\\/'
    match = re.match(pattern, key)
    if match is None:
        raise ValueError(f'no username in object key: {key}')
    return match.group(1)


def get_username_from_inbox_key(key: str) -> str:
    """Extracts the username from a given object key in the inbox.

    :raises ValueError: if ``key`` is not in the inbox.
    """
    return get_username_from_key('inbox', key)


def get_username_from_staging_outbox_key(key: str) -> str:
    """Extracts the username from a given object key in the staging outbox.

    :raises ValueError: if ``key`` is not in the staging outbox.
    """
    return get_username_from_key('staging', key)


def load_json(s3_client, object_key: ObjectKey) -> Dict[str, Any]:
    """Loads a JSON object in an S3 bucket.

    :param boto3.client('s3') s3_client: S3 client to access the object.

    :raises NotFoundError: if the object is not found.

    :raises ValueError: if the loaded object is not JSON-formatted.
    """
    LOGGER.debug('loading object: %s', object_key)
    try:
        res = s3_client.get_object(
            Bucket=object_key['bucket'],
            Key=object_key['key'],
        )
    except s3_client.exceptions.NoSuchKey as exc:
        raise NotFoundError(f'no such object: {object_key}') from exc
    body = res['Body']
    data = body.read()
    body.close()
    return json.loads(data.decode('utf-8'))


def load_object(s3_client, object_key: ObjectKey) -> DictObject:
    """Loads a specified object from the S3 bucket as an ActivityStreams
    object.

    :param boto3.client('s3') s3_client: S3 client to access the object.

    :raises NotFoundError: if the object is not found.

    :raises ValueError: if the loaded object is not JSON-formatted.

    :raises TypeError: if the loaded object is incompatible with
    ActivityStreams object.
    """
    obj = load_json(s3_client, object_key)
    return DictObject(obj)


def load_activity(s3_client, object_key: ObjectKey) -> Activity:
    """Loads a specified activity from the S3 bucket as an activity object.

    :param boto3.client('s3') s3_client: S3 client to access the object.

    :raises NotFoundError: if the object is not found.

    :raises ValueError: if the loaded object is not JSON-formatted.

    :raises TypeError: if the loaded object does not represent an activity.
    """
    obj = load_json(s3_client, object_key)
    return Activity.parse_object(obj)


def save_object(s3_client, object_key: ObjectKey, obj: DictObject):
    """Saves a given ActivityStreams object in the S3 bucket.

    :param boto3.client('s3') s3_client: S3 client to access the bucket.
    """
    LOGGER.debug('saving object: %s', object_key)
    res = s3_client.put_object(
        Bucket=object_key['bucket'],
        Key=object_key['key'],
        Body=json.dumps(obj.to_dict()).encode('utf-8')
    )
    LOGGER.debug('saved object: %s', res)


def save_activity_in_outbox(s3_client, bucket_name: str, activity: Activity):
    """Saves a given activity in the outbox.

    :param boto3.client('s3') s3_client: S3 client to access the bucket.

    :raises AttributeError: if ``activity`` does not have ``id``.

    :raises ValueError: if ``activity.id`` is malformed.
    """
    _, username, unique_part = parse_user_activity_id(activity.id)
    save_object(
        s3_client,
        {
            'bucket': bucket_name,
            'key': f'outbox/users/{username}/{unique_part}.json',
        },
        activity,
    )


def save_post(s3_client, bucket_name: str, post: Note):
    """Saves a given post ("Note" object) in the objects folder.

    :param boto3.client('s3') s3_client: S3 client to access the bucket.

    :raises AttributeError: if ``post`` does not have ``id``.

    :raises ValueError: if ``post.id`` is malformed.
    """
    _, username, unique_part = parse_user_post_id(post.id)
    save_object(
        s3_client,
        {
            'bucket': bucket_name,
            'key': f'objects/users/{username}/posts/{unique_part}.json',
        },
        post,
    )
