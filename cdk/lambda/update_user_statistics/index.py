# -*- coding: utf-8 -*-

"""Updates statistics on the user table.

You have to specify the following environment variable:
* ``USER_TABLE_NAME``: name of the DynamoDB table that manages user information.
"""

import logging
import os
from typing import Any, Dict, Generator
import boto3
from boto3.dynamodb.types import TypeDeserializer
from libmumble.dynamodb import PrimaryKey, dict_as_primary_key
from libmumble.user_table import (
    UserTable,
    make_user_partition_key,
    parse_followee_partition_key,
    parse_follower_partition_key,
)
from libmumble.utils import chunk


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

BATCH_SIZE = 25 # hard limit upon items in a single batch of DynamoDB

USER_TABLE_NAME = os.environ['USER_TABLE_NAME']

DESERIALIZER = TypeDeserializer()


def deserialize_primary_key(key: Dict[str, Any]) -> PrimaryKey:
    """Converts a given primary key in a DynamoDB stream event into
    ``PrimaryKey``.

    :raises TypeError: if ``key`` is not a valid user table primary key.
    """
    return dict_as_primary_key(
        DESERIALIZER.deserialize({
            'M': key,
        }),
    )


class UserUpdates: # pylint: disable=too-few-public-methods
    """Accumulated updates on a user.
    """
    username: str
    """Username."""
    delta_follower_count: int = 0
    """Number added to the number of followers of the user."""
    delta_followee_count: int = 0
    """Number added to the number of accounts followed by the user."""

    def __init__(self, username: str):
        """Initializes with a username.
        """
        self.username = username

    def make_statement(self, table_name: str):
        """Makes a PartiQL statement to execute the updates.
        """
        return {
            'Statement': (
                f'UPDATE "{table_name}"'
                ' SET followerCount = followerCount + ?'
                ' SET followingCount = followingCount + ?'
                " WHERE pk = ? AND sk = 'reserved'"
            ),
            'Parameters': [
                { 'N': str(self.delta_follower_count) },
                { 'N': str(self.delta_followee_count) },
                { 'S': make_user_partition_key(self.username) },
            ],
        }


class Updates:
    """Updates on the user table.
    """
    user_updates: Dict[str, UserUpdates]
    """Maps a username to accumulated updates."""
        # DO NOT initialize it here. Otherwise, you will end up with infinite
        # invocations because the updates are accumulated over different calls.

    def __init__(self):
        """Initializes an empty updates.
        """
        self.user_updates = {}

    def get_user_updates(self, username: str) -> UserUpdates:
        """Returns the updates object for a given user.

        Initializes an empty object if there is no updates object for the user.
        """
        if username not in self.user_updates:
            self.user_updates[username] = UserUpdates(username)
        return self.user_updates[username]

    def process_record(self, record: Dict[str, Any]):
        """Processes a given record.

        Does not actually updates the database but accumulates updates.
        Call ``execute`` to update the database.

        :raises TypeError: if the key is not a valid user table primary key.
        """
        event_name = record['eventName']
        if event_name == 'INSERT':
            self.process_insert(
                deserialize_primary_key(record['dynamodb']['Keys']),
            )
        elif event_name == 'REMOVE':
            self.process_remove(
                deserialize_primary_key(record['dynamodb']['Keys']),
            )
        else:
            LOGGER.debug('ignores event: %s', event_name)

    def process_insert(self, key: PrimaryKey):
        """Processes an "INSERT" event.
        """
        pk = key['pk'] # pylint: disable=invalid-name
        if pk.startswith(UserTable.FOLLOWER_PK_PREFIX):
            LOGGER.debug('incrementing follower')
            self.add_follower_count(key, 1)
        elif pk.startswith(UserTable.FOLLOWEE_PK_PREFIX):
            LOGGER.debug('incrementing followee')
            self.add_followee_count(key, 1)
        else:
            LOGGER.debug('ignores key: %s', key)

    def process_remove(self, key: PrimaryKey):
        """Processes a "REMOVE" event.
        """
        pk = key['pk'] # pylint: disable=invalid-name
        if pk.startswith(UserTable.FOLLOWER_PK_PREFIX):
            LOGGER.debug('decrementing follower')
            self.add_follower_count(key, -1)
        elif pk.startswith(UserTable.FOLLOWEE_PK_PREFIX):
            LOGGER.debug('decrementing followee')
            self.add_followee_count(key, -1)
        else:
            LOGGER.debug('ignores key: %s', key)

    def add_follower_count(self, key: PrimaryKey, delta: int):
        """Adds a given number to the follower count of a user.

        :raises ValueError: if ``key`` is not a valid follower key.
        """
        username = parse_follower_partition_key(key['pk'])
        self.get_user_updates(username).delta_follower_count += delta

    def add_followee_count(self, key: PrimaryKey, delta: int):
        """Adds a given number to the followee count of a user.

        :raises ValueError: if ``key`` is not a valid followee key.
        """
        username = parse_followee_partition_key(key['pk'])
        self.get_user_updates(username).delta_followee_count += delta

    def execute(self):
        """Executes the accumulated updates.
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
                    # TODO: we should not retry execution.
                    #       should we report error to SQS?

    def enumerate_statements(self) -> Generator[Dict[str, Any], None, None]:
        """Enumerates statements to update statistics.
        """
        for updates in self.user_updates.values():
            yield updates.make_statement(USER_TABLE_NAME)


def lambda_handler(event, _context):
    """Runs on AWS Lambda.

    Supposed to be triggered by a DynamoDB stream.
    """
    updates = Updates()
    LOGGER.debug('collecting updates')
    for record in event['Records']:
        updates.process_record(record)
    LOGGER.debug('executing updates')
    updates.execute()
