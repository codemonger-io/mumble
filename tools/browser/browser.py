# -*- coding: utf-8 -*-

"""Browser on ActivityPub networks.

A collection of commands to retrieve and parse information from ActivityPub
networks for traversal.
"""

import json
import logging
import sys
from typing import Any, Dict, List, Optional, Union
import click
import jmespath
import requests


LOGGER = logging.getLogger(__name__)

ACTIVITY_STREAM_MIME_TYPES = [
    'application/activity+json',
    'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
]

DEFAULT_ACTIVITY_STREAM_MIME_TYPE = (
    'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'
)


def read_stdin() -> str:
    """Reads the next line from the standard input.

    Trailing line ending characters are removed.
    """
    return sys.stdin.readline().rstrip()


def get_account_domain(account: str) -> str:
    """Returns the domain of a given account.

    ``account`` must be in the form "<name>@<domain-name>"; e.g.,
    "gargron@mastodon.social".

    :raises ValueError: if ``account`` does not contain an atmark ('@').
    """
    _, domain = account.split('@', maxsplit=1)
    return domain


def print_jmespath_match(value: Any, query: str) -> Any:
    """Filters a given value with a specified JMESPath expression prints
    matching results.

    If the matching result is an ``str``, prints it as a string.
    Otherwise, prints it in a JSON representation.
    """
    match = jmespath.search(query, value)
    if type(match) == str:
        print(match)
    else:
        print(json.dumps(match, indent='  '))


def save_json(value: Any, json_path: str):
    """Saves a given value in a specified file in a JSON representation.
    """
    with open(json_path, mode='w', encoding='utf-8') as json_out:
        json.dump(value, json_out, indent='  ')


def resolve_collection_page(page: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Resolves a given collection page.

    ``page`` may be a URI, a link object, or a collection page itself.
    """
    # resolves the page if necessary
    page_ref: Optional[str] = None
    if type(page) == str:
        page_ref = page
    elif page.get('type') == 'Link':
        page_ref = page['href']
    if page_ref is not None:
        res = requests.get(page_ref, headers={
            'Accept': DEFAULT_ACTIVITY_STREAM_MIME_TYPE,
        })
        res.raise_for_status()
        page = res.json()
    return page


@click.group()
@click.option('--debug', is_flag=True, help='turns on debug messages')
def cli(debug: bool):
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
    try:
        domain = get_account_domain(account)
    except ValueError:
        LOGGER.error(
            'ACCOUNT must be in the form "<name>@<domain-name>";'
            ' e.g., gargron@mastodon.social',
        )
        sys.exit(1)
    endpoint = f'https://{domain}/.well-known/webfinger?resource=acct:{account}'
    LOGGER.debug('getting: %s', endpoint)
    res = requests.get(endpoint, headers={
        'Accept': 'application/json',
    })
    res.raise_for_status()
    data = res.json()
    if dump:
        LOGGER.debug('saving WebFinger results: %s', dump)
        save_json(data, dump)
    # locates the link with ActivityStream mime-type
    # chooses the one with rel=self if there are more than one such links
    links = data['links']
    links = [l for l in links if l.get('type') in ACTIVITY_STREAM_MIME_TYPES]
    if len(links) > 1:
        LOGGER.warning('there are more than one actor URIs: %d', len(links))
        links = [l for l in links if l.get('rel') == 'self']
        if len(links) > 1:
            # warns but chooses the first link
            LOGGER.warning(
                'there are more than one "self" actor URIs: %d',
                len(links),
            )
    print(links[0]['href'])


# keys of an actor to be printed by default.
ACTOR_DEFAULT_OUTPUT_KEYS = [
    'name',
    'preferredUsername',
    'inbox',
    'outbox',
    'following',
    'followers',
    'featured',
    'featuredTags',
]


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
def actor(actor: str, query: Optional[str], dump: Optional[str]):
    """Obtains an actor.

    ACTOR is the actor URI to obtain the profile.
    The actor URI is read from the standard input if ACTOR is '-'.
    """
    if actor == '-':
        LOGGER.debug('reading ACTOR from STDIN')
        actor = read_stdin()
    LOGGER.debug('getting profile: %s', actor)
    res = requests.get(actor, headers={
        'Accept': DEFAULT_ACTIVITY_STREAM_MIME_TYPE,
    })
    res.raise_for_status()
    data = res.json()
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
    collection: str,
    page: int,
    query: Optional[str],
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
    res = requests.get(collection, headers={
        'Accept': DEFAULT_ACTIVITY_STREAM_MIME_TYPE,
    })
    res.raise_for_status()
    data = res.json()
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
def object(object: str, query: Optional[str], dump: Optional[str]):
    """Obtains an object.

    OBJECT is the object URI to obtain.
    The object URI is read from the standard input if OBJECT is '-'.
    """
    if object == '-':
        LOGGER.debug('reading OBJECT from STDIN')
        object = read_stdin()
    LOGGER.debug('obtaining object: %s', object)
    res = requests.get(object, headers={
        'Accept': DEFAULT_ACTIVITY_STREAM_MIME_TYPE,
    })
    res.raise_for_status()
    data = res.json()
    if dump is not None:
        LOGGER.debug('saving the pulled object: %s', dump)
        save_json(data, dump)
    LOGGER.debug('filtering object with: %s', query)
    print_jmespath_match(data, query)


if __name__ == '__main__':
    cli()
