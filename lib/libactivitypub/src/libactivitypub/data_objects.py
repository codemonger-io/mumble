# -*- coding: utf-8 -*-

"""Defines ActivityStreams object representing data.
"""

import logging
from typing import Any, Dict, List, Union
from .objects import DictObject


LOGGER = logging.getLogger('libactivitypub.data_objects')
LOGGER.setLevel(logging.DEBUG)


class Note(DictObject):
    """Wraps a "Note" object.
    """
    def __init__(self, underlying: Dict[str, Any]):
        """Wraps a given ``dict`` representing a "Note".

        :raises ValueError: if ``underlying`` does not represent an object,
        or if ``underlying`` does not have "content".

        :raises TypeError: if ``underlying`` is incompatible with
        ActivityStreams object, or if "content" of ``underlying`` is not
        ``str``.
        """
        super().__init__(underlying)
        if 'content' not in underlying:
            raise ValueError('invalid note: missing content')
        if not isinstance(underlying['content'], str):
            raise TypeError(
                f'content must be str but {type(underlying["content"])}',
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

    @property
    def published(self) -> str:
        """"published" property.

        :raises AttributeError: if "published" is missing.
        """
        if 'published' not in self._underlying:
            raise AttributeError('no "published" property')
        return self._underlying['published']

    @published.setter
    def published(self, value: str):
        self._underlying['published'] = value

    @property
    def to(self) -> Union[str, List[str]]: # pylint: disable=invalid-name
        """"to" property.

        :raises AttributeError: if "to" is missing.
        """
        if 'to' not in self._underlying:
            raise AttributeError('no "to" property')
        return self._underlying['to']

    @to.setter
    def to(self, value: Union[str, List[str]]): # pylint: disable=invalid-name
        self._underlying['to'] = value

    @property
    def cc(self) -> Union[str, List[str]]: # pylint: disable=invalid-name
        """"cc" property.

        :raises AttributeError: if "cc" is missing.
        """
        if 'cc' not in self._underlying:
            raise AttributeError('no "cc" property')
        return self._underlying['cc']

    @cc.setter
    def cc(self, value: Union[str, List[str]]): # pylint: disable=invalid-name
        self._underlying['cc'] = value

    @property
    def bcc(self):
        """"bcc" property.

        :raises AttributeError: if "bcc" is missing.
        """
        if 'bcc' not in self._underlying:
            raise AttributeError('no "bcc" property')
        return self._underlying['bcc']

    @bcc.setter
    def bcc(self, value: Union[str, List[str]]):
        self._underlying['bcc'] = value
