# -*- coding: utf-8 -*-

"""Defines common MIME types.
"""

from typing import List


ACTIVITY_STREAM_MIME_TYPES: List[str] = [
    'application/activity+json',
    'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
]
"""MIME types for ActivityStream."""

DEFAULT_ACTIVITY_STREAM_MIME_TYPE: str = (
    'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'
)
"""Default MIME type for ActivityStream."""
