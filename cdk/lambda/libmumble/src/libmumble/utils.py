# -*- coding: utf-8 -*-

"""Provides miscellaneous utilities.
"""

def to_urlsafe_base64(b64: str) -> str:
    """Converts a standard Base64-encoded string into a URL-safe string.

    Replaces '+' with '-', and '/' with '_'.
    Removes trailing '='.
    """
    return b64.rstrip('=').replace('+', '-').replace('/', '_')
