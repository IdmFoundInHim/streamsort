""" StreamSort utility functions

Copyright (c) 2020 IdmFoundInHim, except where otherwise credited
"""

from typing import Iterator
from itertools import cycle, islice

import requests
try:
    from spotipy import SpotifyPKCE
except ImportError:
    from spotipy import SpotifyImplicitGrant as SpotifyPKCE

from constants import MOBNAMES
from musictypes import Mob

def get_header(oauth: str) -> dict:
    """ Returns header with given oauth for the Spotify API """
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {oauth}",
    }


def results_generator(auth: SpotifyPKCE, page_zero: dict) -> Iterator[Mob]:
    """ Cycles through multi-page responses from Spotify """
    if not all(k in page_zero for k in ['items', 'next']):
        raise ValueError
    yield from page_zero['items']
    if not page_zero['next']:
        return
    page = {'next': page_zero['next']}
    header = get_header(auth.get_access_token())
    while nexturl := page['next']:
        try:
            page_r = requests.get(nexturl, headers=header)
            page_r.raise_for_status()
            page = page_r.json()
            yield from page['items']
        except requests.exceptions.HTTPError:
            header = get_header(auth.get_access_token(check_cache=False))
            page = {'next': nexturl}
        except KeyError:
            key = next((n + 's' for n in MOBNAMES if n + 's' in page), 'items')
            yield from page[key]['items']


def roundrobin(*iterables):
    "roundrobin('ABC', 'D', 'EF') --> A D E B F C"
    # From the Python documentation on itertools
    # https://docs.python.org/3/library/itertools.html#itertools-recipes
    # Recipe credited to George Sakkis
    num_active = len(iterables)
    nexts = cycle(iter(it).__next__ for it in iterables)
    while num_active:
        try:
            for next in nexts: # pylint: disable=redefined-builtin
                yield next()
        except StopIteration:
            # Remove the iterator we just exhausted from the cycle.
            num_active -= 1
            nexts = cycle(islice(nexts, num_active))


def first_true(iterable, default=False, pred=None):
    """Returns the first true value in the iterable.

    If no true value is found, returns *default*

    If *pred* is not None, returns the first item
    for which pred(item) is true.

    """
    # From the Python documentation on itertools
    # https://docs.python.org/3/library/itertools.html#itertools-recipes

    # first_true([a,b,c], x) --> a or b or c or x
    # first_true([a,b], x, f) --> a if f(a) else b if f(b) else x
    return next(filter(pred, iterable), default)
