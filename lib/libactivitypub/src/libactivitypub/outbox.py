# -*- codint: utf-8 -*-

"""Provides access to outbox.
"""

import logging
from typing import Generator, Optional
from .activity import Activity
from .activity_stream import get as activity_stream_get
from .collection import resolve_collection_page


LOGGER = logging.getLogger('libactivitypub.outbox')
LOGGER.setLevel(logging.DEBUG)


class Outbox:
    """Wraps an outbox.
    """
    def __init__(self, outbox_uri: str):
        """Initializes with a given outbox URI.
        """
        self.outbox_uri = outbox_uri

    def __iter__(self) -> Generator[Activity, None, None]:
        """Iterates over activities in the outbox.

        :raises requests.HTTPError: if an HTTP request fails.
        """
        LOGGER.debug('pulling outbox collection: %s', self.outbox_uri)
        collection = activity_stream_get(self.outbox_uri)
        items = collection.get('items') or collection.get('orderedItems')
        next_page: Optional[str] = None # URI of the next page
        if items is None:
            # obtains the first page if there is no `items` or `orderedItems`
            LOGGER.debug('pulling the first page: %s', collection['first'])
            page_data = resolve_collection_page(collection['first'])
            items = page_data.get('items') or page_data.get('orderedItems')
            next_page = page_data.get('next')
        # yields each item until all the items are exhausted
        current_page = 1
        while items is not None:
            for item in items:
                yield Activity.parse_object(item)
            # resolves the next page if exists
            if next_page is None:
                break
            current_page += 1
            LOGGER.debug('pulling the page[%d]: %s', current_page, next_page)
            page_data = resolve_collection_page(next_page)
            items = page_data.get('items') or page_data.get('orderedItems')
            next_page = page_data.get('next')
