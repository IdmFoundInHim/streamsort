from typing import Callable, Iterator

import requests
from spotipy import SpotifyImplicitGrant

from constants import MOBNAMES


def get_property(obj: dict, property_name: str):
    try:
        return obj[property_name]
    except KeyError:
        return None


def get_header(oauth: str) -> dict:
    """ Returns header with given oauth for the Spotify API """
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {oauth}",
    }


def results_generator(auth: SpotifyImplicitGrant,
                      page_zero: dict) -> Iterator[dict]:
    if not all(k in page_zero for k in ['items', 'next']):
        raise ValueError
    yield from page_zero['items']
    if not page_zero['next']:
        return
    page = {'next': page_zero['next']}
    header = get_header(auth.get_access_token())
    while nexturl := page['next']:
        try:
            page = requests.get(nexturl, headers=header)
            page.raise_for_status()
            page = page.json()
            yield from page['items']
        except requests.exceptions.HTTPError:
            header = get_header(auth.get_access_token(check_cache=False))
            page = {'next': nexturl}
        except KeyError:
            key = [n + 's' for n in MOBNAMES if n + 's' in page] or ['items']
            yield from page[key]['items']
