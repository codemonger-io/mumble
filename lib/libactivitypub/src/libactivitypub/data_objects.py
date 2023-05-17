# -*- coding: utf-8 -*-

"""Defines ActivityStreams object representing data.
"""

import logging
from typing import Any, Dict
from .objects import DictObject


LOGGER = logging.getLogger('libactivitypub.data_objects')
LOGGER.setLevel(logging.DEBUG)

COLLECTION_TYPES = ['Collection', 'OrderedCollection']
"""Types representing a collection."""


class Note(DictObject):
    """Wraps a "Note" object.
    """
    def __init__(self, underlying: Dict[str, Any]):
        """Wraps a given ``dict`` representing a "Note".

        :raises ValueError: if ``underlying`` does not represent an object,
        or if ``underlying`` does not have "content".

        :raises TypeError: if ``underlying`` is incompatible with
        ActivityStreams object,
        or if ``underlying`` has no "content",
        or if ``underlying`` has a non-str "content",
        or if ``underlying`` has a non-str "attributedTo".
        """
        super().__init__(underlying)
        if 'content' not in underlying:
            raise TypeError('invalid note: missing content')
        if not isinstance(underlying['content'], str):
            raise TypeError(
                f'content must be str but {type(underlying["content"])}',
            )
        if (
            'attributedTo' in underlying
            and not isinstance(underlying['attributedTo'], str)
        ):
            raise TypeError(
                'attributedTo must be str but'
                f' {type(underlying["attributedTo"])}',
            )

    @property
    def attributed_to(self) -> str:
        """"attributedTo" property.

        :raises AttributeError: if "attributedTo" is missing.
        """
        if 'attributedTo' not in self._underlying:
            raise AttributeError('no "attributedTo" property')
        return self._underlying['attributedTo']

    @attributed_to.setter
    def attributed_to(self, value: str):
        self._underlying['attributedTo'] = value
