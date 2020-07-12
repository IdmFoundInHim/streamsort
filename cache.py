import json
from datetime import datetime as dt
from typing import Optional

from spotipy import Spotify, SpotifyImplicitGrant
from utilities import results_generator


def liked_songs_cache_check(api: Spotify):
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
    latest = api.current_user_saved_tracks()
    if ((dt.now() - dt.fromisoformat(cached['as_of'])).days > 6
            or latest['total'] != cached['total']):
        _liked_songs_cache_save(api.auth_manager, latest)
        return latest
    return cached


def _liked_songs_cache_save(auth: SpotifyImplicitGrant, page_zero: dict):
    pending = {}
    pending['total'] = page_zero['total']
    pending['as_of'] = dt.now().isoformat()
    tracks, albums, artists = set(), set(), set()
    for t in results_generator(auth, page_zero):
        t = t['track']
        tracks.add(t['id'])
        albums.add(t['album']['id'])
        for a in t['artists']:
            artists.add(a['id'])
    pending['track'] = list(tracks)
    pending['album'] = list(albums)
    pending['artist'] = list(artists)
    with open(".cache/likedsongs.json", 'w') as cache:
        return json.dump(pending, cache)
