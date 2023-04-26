# -*- coding: utf-8 -*-

"""Provides access to inbox.
"""

import logging


LOGGER = logging.getLogger('libactivity.inbox')
LOGGER.setLevel(logging.DEBUG)


class Inbox:
    """Wraps an inbox.
    """
    def __init__(self, inbox_uri: str):
        """Initialized with a given inbox URI.
        """
        self.inbox_uri = inbox_uri

    @property
    def uri(self) -> str:
        """URI of the inbox.
        """
        return self.inbox_uri
