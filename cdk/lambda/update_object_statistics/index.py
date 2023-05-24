# -*- coding: utf-8 -*-

"""Updates statistics on the object table.

You have to specify the following environment variable:
* ``OBJECT_TABLE_NAME``: name of the DynamoDB table that manages objects.
"""

import logging
import os
from typing import Any, Dict, Generator
import boto3
from boto3.dynamodb.types import TypeDeserializer
from libmumble.dynamodb import PrimaryKey, dict_as_primary_key
from libmumble.object_table import ObjectTable
from libmumble.utils import chunk


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

BATCH_SIZE = 25 # hard limit upon items in a single batch for DynamoDB

OBJECT_TABLE_NAME = os.environ['OBJECT_TABLE_NAME']
OBJECT_TABLE = ObjectTable(boto3.resource('dynamodb').Table(OBJECT_TABLE_NAME))

DESERIALIZER = TypeDeserializer()


def deserialize_key(value: Dict[str, Any]) -> Dict[str, Any]:
    """Converts a given primary key partially represented in the DynamoDB
    convention into the corresponding Python type.
    """
    return DESERIALIZER.deserialize({
        'M': value,
    })


class Updates:
    """Updates on statistics.
    """
    post_updates: Dict[str, 'PostUpdates']
    """Maps a partition key of a post to the updates to the post."""
        # DO NOT initialize it here. Otherwise, you will end up with infinite
        # invocations because the updates in the previous call persist.

    def __init__(self):
        """Initializes an empty updates.
        """
        self.post_updates = {}

    def process_record(self, record: Dict[str, Any]):
        """Processes a given event record.

        Does not actually update the database but accumulates the deltas added
        to statistics.
        Call ``execute`` to actually update the database.

        :raises TypeError: if the primary key is invalid.
        """
        event_name = record['eventName']
        if event_name == 'INSERT':
            key = dict_as_primary_key(
                deserialize_key(record['dynamodb']['Keys']),
            )
            self.process_insert(key)
        elif event_name == 'REMOVE':
            key = dict_as_primary_key(
                deserialize_key(record['dynamodb']['Keys']),
            )
            self.process_remove(key)
        else:
            LOGGER.debug('ignores event: %s', event_name)

    def process_insert(self, key: PrimaryKey):
        """Processes an "INSERT" event.
        """
        if key['pk'].startswith(ObjectTable.OBJECT_PK_PREFIX):
            if key['sk'].startswith(ObjectTable.REPLY_SK_PREFIX):
                self.add_reply_count(key, 1)
            else:
                LOGGER.debug('ignores other than post')
        else:
            LOGGER.debug('ignores non-object')

    def process_remove(self, key: PrimaryKey):
        """Processes a "REMOVE" event.
        """
        if key['pk'].startswith(ObjectTable.OBJECT_PK_PREFIX):
            if key['sk'].startswith(ObjectTable.REPLY_SK_PREFIX):
                self.add_reply_count(key, -1)
            else:
                LOGGER.debug('ignores other than post')
        else:
            LOGGER.debug('ignores non-object')

    def add_reply_count(self, key: PrimaryKey, delta: int):
        """Adds a given number to the numbrer of replies to the original post.
        """
        LOGGER.debug('adding reply: key=%s, delta=%d', key, delta)
        post_pk = key['pk']
        if post_pk not in self.post_updates:
            self.post_updates[post_pk] = PostUpdates(post_pk)
        self.post_updates[post_pk].delta_reply_count += delta

    def execute(self):
        """Executes the updates.
        """
        dynamodb = boto3.client('dynamodb')
        batches = chunk(self.enumerate_statements(), BATCH_SIZE)
        for i, batch in enumerate(batches):
            LOGGER.debug('executing batch [%d]: %s', i, batch)
            res = dynamodb.batch_execute_statement(Statements=batch)
            for j, res_item in enumerate(res['Responses']):
                if 'Error' in res_item:
                    LOGGER.error(
                        'update error: error=%s, statement=%s',
                        res_item['Error'],
                        batch[j],
                    )
                    # TODO: we should not repeat processing.
                    #       should we report error to SQS?

    def enumerate_statements(self) -> Generator[Dict[str, Any], None, None]:
        """Enumerates statements to update statistics.
        """
        for updates in self.post_updates.values():
            yield updates.make_statement(OBJECT_TABLE_NAME)


class PostUpdates: # pylint: disable=too-few-public-methods
    """Updates on a post.
    """
    post_pk: str
    """Partition key of the original post."""
    delta_reply_count: int = 0
    """The number added to the number of replies."""

    def __init__(self, post_pk: str):
        """Initializes updates on a given post.

        :param str post_pk: partition key of the original post.
        """
        self.post_pk = post_pk

    def make_statement(self, table_name: str):
        """Makes a PartiQL statement to execute the updates.
        """
        return {
            'Statement': (
                f'UPDATE "{table_name}"'
                ' SET replyCount = replyCount + ?'
                " WHERE pk = ? AND sk = 'metadata'"
            ),
            'Parameters': [
                { 'N': str(self.delta_reply_count) },
                { 'S': self.post_pk },
            ],
        }


def lambda_handler(event, _context):
    """Runs on AWS Lambda.

    ``event`` must be from DynamoDB stream.
    """
    LOGGER.debug('collecting statistics: %s', event)
    updates = Updates()
    for record in event['Records']:
        updates.process_record(record)
    LOGGER.debug('updating statisitcs')
    updates.execute()
