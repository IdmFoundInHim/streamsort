""" StreamSort utility functions

Copyright (c) 2020 IdmFoundInHim, except where otherwise credited
"""

from typing import cast, Iterator, Mapping
import urllib

from more_itertools import flatten
import requests
from spotipy import Spotify, SpotifyPKCE

from .constants import (MOBNAMES, MOB_URI_PREFIX, MOB_URL_PREFIX,
                        SPID_VALID_CHARS)
from .musictypes import Mob

def get_header(oauth: str) -> dict:
    """ Returns header with given oauth for the Spotify API """
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {oauth}",
    }


def results_generator(auth: SpotifyPKCE, page_zero: Mapping) -> Iterator[Mob]:
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
            if 'offset=2000' in nexturl:
                return
            header = get_header(auth.get_access_token(check_cache=False))
            page = {'next': nexturl}
        except KeyError:
            key = next((n + 's' for n in MOBNAMES if n + 's' in page), 'items')
            page = page[key]
            yield from page['items']


def contains_uri(uri: str):
    """ Returns the URI in standard format only if present """
    if uri.startswith(MOB_URL_PREFIX):
        try:
            url = urllib.parse.urlparse(uri)
        except ValueError:
            return ''
        uri = MOB_URI_PREFIX + ':'.join(url.path.split('/')[-2:])
    uri_parts = uri.strip().split(':')
    if (len(uri_parts) == 3
       and uri_parts[0] == 'spotify'
       and uri_parts[1] in MOBNAMES
       and all(c in SPID_VALID_CHARS for c in uri_parts[2])):
        return uri
    return ''


def _track_in_mob(api: Spotify, track: Mob, mob: Mob) -> bool:
    if mob['type'] == 'artist':
        return mob['id'] in (a['id'] for a in track['artists'])
    if mob['type'] == 'album':
        breakpoint()
        return track['id'] in (t['id'] for t
                               in results_generator(api.auth_manager,
                                                    mob['tracks']))
    if mob['type'] == 'playlist':
        return (track['id']
                in (t['id'] for t
                    in results_generator(api.auth_manager,
                                         cast(dict,
                                              api.playlist_items(mob['id'])))))
    return False


def _album_in_mob(api: Spotify, album: Mob, mob: Mob) -> bool:
    if mob['type'] == 'artist':
        return mob['id'] in (a['id'] for a in album['artists'])
    if mob['type'] == 'playlist':
        return (album['id'] in
                (t['album']['id'] for t
                 in results_generator(api.auth_manager,
                                      cast(dict, api.playlist_items(mob['id']))
                ))                    )
    return False


def _artist_in_mob(api: Spotify, artist: Mob, mob: Mob) -> bool:
    if mob['type'] == 'track':
        return artist['id'] in (a['id'] for a in mob['artists'])
    if mob['type'] == 'album':
        return (artist['id'] in
                flatten(t['artists'] for t
                        in results_generator(api.auth_manager, mob['tracks'])))
    if mob['type'] == 'playlist':
        return (artist['id'] in
                flatten(t['artists'] for t
                        in results_generator(api.auth_manager,
                                             cast(dict,
                                                  api.playlist_items(mob['id'])
                )       )                    )    )
    return False


_MOB_SPECIFIC_TESTS = {
    'track': _track_in_mob,
    'album': _album_in_mob,
    'artist': _artist_in_mob,
}


def mob_in_mob(api: Spotify, obj: Mob, lst: Mob) -> bool:
    """ Check if a mob is found in another mob
    
    All items contain themselves in addition to anything else.
    Albums are considered to contain their tracks + any
    artists credited on those tracks. Artists are considered to contain
    any tracks they are credited on + any albums or playlists
    containing their tracks. Playlists contain their tracks + any
    albums and artists represented in those tracks.

    TODO doctests here

    Episodes and non-mobs match nothing, but throw no error.

    TODO that especially needs doctesting
    """
    if obj['uri'] == lst['uri']:
        return True
    if test := _MOB_SPECIFIC_TESTS.get(obj['type']):
        return test(api, obj, lst)
    return False
