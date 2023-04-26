# -*- coding: utf-8 -*-

"""Provides access to collections.
"""

import logging
from typing import Any, Dict, Union
from .activity_streams import get as activity_streams_get


LOGGER = logging.getLogger('libactivitypub.collection')
LOGGER.setLevel(logging.DEBUG)


def resolve_collection_page(
    page: Union[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Resolves a given collection page.

    ``page`` may be a URI, a link object, or a collection page itself.

    :raises requests.HTTPError: if an HTTP request fails.
    """
    page_ref: str
    if isinstance(page, str):
        page_ref = page
    elif page.get('type') == 'Link':
        page_ref = page['href']
    else:
        # page is probably a collection page itself
        return page
    return activity_streams_get(page_ref)
