# -*- coding: utf-8 -*-

"""Browser on ActivityPub networks.

A collection of commands to retrieve and parse information from ActivityPub
networks for traversal.
"""

import itertools
import json
import logging
import sys
from typing import Any, Dict, Generator, Iterable, List, Optional
import click
import jmespath
from libactivitypub.activity import Activity
from libactivitypub.activity_stream import get as activity_stream_get
from libactivitypub.actor import Actor, WebFinger
from libactivitypub.collection import resolve_collection_page


LOGGER = logging.getLogger(__name__)


def read_stdin() -> str:
    """Reads the next line from the standard input.

    Trailing line ending characters are removed.
    """
    return sys.stdin.readline().rstrip()


def print_jmespath_match(value: Any, query: str) -> Any:
    """Filters a given value with a specified JMESPath expression prints
    matching results.

    If the matching result is an ``str``, prints it as a string.
    Otherwise, prints it in a JSON representation.
    """
    match = jmespath.search(query, value)
    if isinstance(match, str):
        print(match)
    else:
        print(json.dumps(match, indent='  '))


def save_json(value: Any, json_path: str):
    """Saves a given value in a specified file in a JSON representation.
    """
    with open(json_path, mode='w', encoding='utf-8') as json_out:
        json.dump(value, json_out, indent='  ')


def filter_activities(
    activities: Iterable[Activity],
    filter_: str,
) -> Generator[Activity, None, None]:
    """Applies JMESPath expression to each activity given by an iterable.

    ``filter_`` is a JMESPath expression that is not applied to the entire
    collection (array) but to individual activities.

    Activities that becomes ``None`` as a result of ``filter_`` will be
    omitted.

    Returns a generator of activities.
    Note that the results of ``quer`` are discarded.
    """
    expression = jmespath.compile(filter_)
    for activity in activities:
        filtered = expression.search(activity._underlying) # pylint: disable=protected-access
        if filtered is not None:
            yield activity


@click.group()
@click.option('--debug', is_flag=True, help='turns on debug messages')
def cli(debug: bool):
    """Simple browser for ActivityPub networks.
    """
    if debug:
        logging.basicConfig(level=logging.DEBUG)
        LOGGER.setLevel(logging.DEBUG)
        # suppresses logs from the dependencies
        logging.getLogger('urllib3').setLevel(logging.INFO)


@cli.command()
@click.argument('account', type=str)
@click.option(
    '--dump',
    metavar='DUMP',
    type=str,
    default=None,
    help=(
        'path to a file where the results from WebFinger are to be saved.'
        ' nothing is saved if omitted.'
    ),
)
def finger(account: str, dump: Optional[str]):
    """WebFingers ACCOUNT and prints the ActivityPub actor URI.

    ACCOUNT is the account to be WebFingered; e.g., gargron@mastodon.social.
    It is read from the standard input if ACCOUNT is '-'.
    """
    if account == '-':
        LOGGER.debug('reading ACCOUNT from STDIN')
        account = read_stdin()
    LOGGER.debug('fingering: %s', account)
    finger_ = WebFinger.finger(account)
    if dump:
        LOGGER.debug('saving WebFinger results: %s', dump)
        save_json(finger_._underlying, dump) # pylint: disable=protected-access
    # locates the link with ActivityStream mime-type
    # chooses the one with rel=self if there are more than one such links
    print(finger_.actor_uri)


@cli.command()
@click.argument('actor', type=str)
@click.option(
    '--query',
    metavar='JMESPATH',
    type=str,
    default='@',
    help=(
        'JMESPath expression the filters information in the pulled actor to be'
        ' printed. all the information is printed if omitted.'
    ),
)
@click.option(
    '--dump',
    metavar='DUMP',
    type=str,
    default=None,
    help=(
        'path to a file where obtained actor information is to be saved.'
        ' nothing is saved if omitted.'
    ),
)
def actor(actor: str, query: str, dump: Optional[str]): # pylint: disable=redefined-outer-name
    """Obtains an actor.

    ACTOR is the actor URI to obtain the profile.
    The actor URI is read from the standard input if ACTOR is '-'.
    """
    if actor == '-':
        LOGGER.debug('reading ACTOR from STDIN')
        actor = read_stdin()
    LOGGER.debug('getting profile: %s', actor)
    data = activity_stream_get(actor)
    if dump is not None:
        LOGGER.debug('saving actor information: %s', dump)
        save_json(data, dump)
    LOGGER.debug('actor id: %s', data['id'])
    LOGGER.debug('filtering actor information with: %s', query)
    print_jmespath_match(data, query)


@cli.command()
@click.argument('collection', type=str)
@click.option(
    '--page',
    metavar='PAGE',
    type=int,
    default=1,
    help='page in the collection to pull. starts from 1 (default).',
)
@click.option(
    '--query',
    metavar='JMESPATH',
    type=str,
    default='@',
    help=(
        'JMESPath expression that filters the information in pulled items to'
        ' be printed. all the items are printed if omitted.'
    ),
)
@click.option(
    '--dump',
    metavar='DUMP',
    type=str,
    default=None,
    help=(
        'path to a file where pulled items are to be saved.'
        ' nothing is saved if omitted.'
    ),
)
def collection(
    collection: str, # pylint: disable=redefined-outer-name
    page: int,
    query: str,
    dump: Optional[str],
):
    """Pulls a collection.

    COLLECTION is the collection URI to be pulled.
    The collection URI is read from the standard input if COLLECTION is '-'.
    """
    assert page >= 1
    if collection == '-':
        LOGGER.debug('reading COLLECTION from STDIN')
        collection = read_stdin()
    LOGGER.debug('pulling collection: %s', collection)
    data = activity_stream_get(collection)
    LOGGER.debug('number of total items: %d', data.get('totalItems'))
    items: Optional[List[Dict[str, Any]]]
    items = data.get('items') or data.get('orderedItems')
    next_page: Optional[str] = None # URI of the next page
    if items is None:
        # obtains the first page if there is no `items` or `orderedItems`
        LOGGER.debug('pulling the first page: %s', data['first'])
        page_data = resolve_collection_page(data['first'])
        items = page_data.get('items') or page_data.get('orderedItems')
        next_page = page_data.get('next')

    # skips pages to `page`
    current_page = 1
    while current_page < page:
        current_page += 1
        LOGGER.debug('pulling the page[%d]: %s', current_page, next_page)
        assert next_page is not None
        page_data = resolve_collection_page(next_page)
        items = page_data.get('items') or page_data.get('orderedItems')
        next_page = page_data.get('next')

    assert items is not None
    LOGGER.debug('number of itmes in the page: %d', len(items))
    if dump is not None:
        LOGGER.debug('saving the pulled items: %s', dump)
        save_json(items, dump)
    LOGGER.debug('filtering items with: %s', query)
    print_jmespath_match(items, query)


@cli.command()
@click.argument('object', type=str)
@click.option(
    '--query',
    metavar='JMESPATH',
    type=str,
    default='@',
    help=(
        'JMESPath expression to filter the information in the obtained object'
        ' to be printed. the entire object is printed if omitted.'
    ),
)
@click.option(
    '--dump',
    metavar='DUMP',
    type=str,
    default=None,
    help=(
        'path to a file where the pulled object is to be saved.'
        ' no object is saved if omitted.'
    ),
)
def object(object: str, query: str, dump: Optional[str]): # pylint: disable=redefined-builtin, redefined-outer-name
    """Obtains an object.

    OBJECT is the object URI to obtain.
    The object URI is read from the standard input if OBJECT is '-'.
    """
    if object == '-':
        LOGGER.debug('reading OBJECT from STDIN')
        object = read_stdin()
    LOGGER.debug('obtaining object: %s', object)
    data = activity_stream_get(object)
    if dump is not None:
        LOGGER.debug('saving the pulled object: %s', dump)
        save_json(data, dump)
    LOGGER.debug('filtering object with: %s', query)
    print_jmespath_match(data, query)


@cli.command()
@click.argument('account', type=str)
@click.option(
    '--num-activities',
    metavar='NACTS',
    type=int,
    default=20,
    help=(
        'number of activities to pull. this number counts activities after'
        ' FILTER is applied. 20 by default.'
    ),
)
@click.option(
    '--filter',
    metavar='FILTER',
    type=str,
    default='@',
    help=(
        'JMESPath expression to filter the pulled activities. this expression'
        ' is applied to each activity, and an activity is collected if this'
        ' expression results in a non-null value (results are discarded). all'
        ' the activities are collected if omitted.'
    ),
)
def pull_activities(account: str, num_activities: int, filter: str): # pylint: disable=redefined-builtin
    """Pulls latest activities from a given account.

    ACCOUNT must be a WebFinger ID; e.g., "gargron@mastodon.social".
    """
    LOGGER.debug('pulling activities from %s', account)
    LOGGER.debug('resolving actor: %s', account)
    actor_ = Actor.resolve_webfinger_id(account)
    LOGGER.debug('pulling activities in the outbox with filter %s', filter)
    activities: Iterable[Activity] = itertools.islice(
        filter_activities(actor_.outbox, filter),
        num_activities,
    )
    print(json.dumps([a._underlying for a in activities], indent='  ')) # pylint: disable=protected-access


if __name__ == '__main__':
    cli({})
