# -*- coding: utf-8 -*-

"""Provides access to activities.
"""

import logging
from typing import Any, Dict


LOGGER = logging.getLogger('libactivitypub.activity')
LOGGER.setLevel(logging.DEBUG)


class Activity:
    """Wraps an activity.
    """
    def __init__(self, underlying: Dict[str, Any]):
        """Wraps a given ``dict`` representing an activity.
        """
        self._underlying = underlying
