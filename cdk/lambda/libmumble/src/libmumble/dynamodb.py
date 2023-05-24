# -*- coding: utf-8 -*-

"""Utilities to deal with DynamoDB tables.
"""

from typing import Any, Dict, TypedDict


class PrimaryKey(TypedDict):
    """Primary key used in the user, and object tables.
    """
    pk: str
    """Partition key."""
    sk: str
    """Sort key."""


def dict_as_primary_key(
    d: Dict[str, Any], # pylint: disable=invalid-name
) -> PrimaryKey:
    """Casts a given ``dict`` as a ``PrimaryKey``.

    :raises TypeError: if ``d`` does not represent a ``PrimaryKey``.
    """
    if 'pk' not in d:
        raise TypeError('PrimaryKey must have pk')
    if not isinstance(d['pk'], str):
        raise TypeError(f'pk is not str but {type(d["pk"])}')
    if 'sk' not in d:
        raise TypeError('PrimaryKey must have sk')
    if not isinstance(d['sk'], str):
        raise TypeError(f'sk is not str but {type(d["sk"])}')
    # above checks cannot convice mypy believe d is PrimaryKey
    return d # type: ignore


class TableWrapper:
    """Base class that wraps a ``dynamodb.Table`` resource of boto3.
    """
    def __init__(self, table):
        """Wraps a given DynamoDB table.

        :param boto3.resource('dynamodb').Table table: DynamoDB table resource.
        """
        self._table = table

    @property
    def exceptions(self):
        """Exceptions raised by the DynamoDB table resource.
        """
        return self._table.meta.client.exceptions

    @property
    def ConditionalCheckFailedException(self): # pylint: disable=invalid-name
        """boto3's ``ConditionalCheckFailedException``.
        """
        return self.exceptions.ConditionalCheckFailedException

    @property
    def ProvisionedThroughputExceededException(self): # pylint: disable=invalid-name
        """boto3's ``ProvisionedThroughputExceededException``.
        """
        return self.exceptions.ProvisionedThroughputExceededException

    @property
    def RequestLimitExceeded(self): # pylint: disable=invalid-name
        """boto3's ``RequestLimitExceeded``.
        """
        return self.exceptions.RequestLimitExceeded
