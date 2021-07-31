""" Caching functions for StreamSort

Copyright (c) 2021 IdmFoundInHim, under MIT License
"""

import json
from collections.abc import Mapping
from datetime import datetime as dt
from typing import Any, cast

from spotipy import Spotify, SpotifyPKCE

from .utilities import results_generator


def liked_songs_cache_check(api: Spotify) -> dict[str, Any]:
    """ Get a dict of the cached liked songs list, updating if needed

    All fields are calculated from saved *tracks*, so an album or artist
    is included with even one associated song.

    Fields:

    - `'track'`: list of track ids
    - `'album'`: list of album ids
    - `'artist'`: list of artist ids
    - `'total'`: int, number of liked songs
    - `'as_of'`: datetime last updated
    """
    try:
        with open(".cache/likedsongs.json") as cache:
            cached = json.load(cache)
    except FileNotFoundError:
        cached = {'as_of': '1970-01-01T00:00:00'}
    latest = cast(dict, api.current_user_saved_tracks())
    if ((dt.now() - dt.fromisoformat(cached['as_of'])).days > 6
            or latest['total'] != cached['total']):
        return _liked_songs_cache_save(cast(SpotifyPKCE, api.auth_manager),
                                       latest)
    return cached


def _liked_songs_cache_save(auth: SpotifyPKCE,
                            page_zero: Mapping[str, Any]) -> dict[str, str]:
    pending = {}
    pending['total'] = page_zero['total']
    pending['as_of'] = dt.now().isoformat()
    tracks, albums, artists = set(), set(), set()
    for result in results_generator(auth, page_zero):
        track = result['track']
        tracks.add(track['id'])
        albums.add(track['album']['id'])
        for artist in track['artists']:
            artists.add(artist['id'])
    pending['track'] = list(tracks)
    pending['album'] = list(albums)
    pending['artist'] = list(artists)
    with open(".cache/likedsongs.json", 'w') as cache:
        json.dump(pending, cache)
    return pending
