import datetime as dt
import json
import urllib.parse as urlparse
from typing import Callable
from textwrap import dedent

import requests as net


def is_oauth(oauth):
    return type(oauth) is str and len(oauth) == 83


def authorize(client64: str) -> str:
    """ Get OAuth key for net to server.

    If a valid, current OAuth key is stored locally in ./APIstate.json,
    it will be retrieved. Otherwise, a request to the server will be
    made with client64 (f"{clientid}:{client_secret}" encoded in Base64)
    for a new OAuth key. This will be stored with a timeout value in
    ./APIstate.json, and the OAuth will be returned.
    """
    with open("APIstate.json", 'r') as local:
        try:
            localdict = json.load(local)
        except json.decoder.JSONDecodeError:
            localdict = {}
    if ('oauth' in localdict and 'timeout' in localdict
       and dt.datetime.now() < dt.datetime.fromisoformat(localdict['timeout'])
       and is_oauth(oauth := localdict['oauth'])):
        return oauth
    header = {
        "Authorization": f"Basic {client64}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = "grant_type=client_credentials"
    requesttime = dt.datetime.now()
    oauth = net.post("https://accounts.spotify.com/api/token",
                     headers=header, data=data).json()
    timeout = requesttime + dt.timedelta(seconds=int(oauth['expires_in']))
    customjson = {
        'oauth': (oauthkey := oauth['access_token']),
        'timeout': timeout.isoformat()
    }
    with open("APIstate.json", 'w') as local:
        json.dump(customjson, local) 
    return oauthkey


def getheader(oauth: str) -> dict:
    """ Returns header with given oauth for the Spotify API """
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {oauth}",
    }


def request(oauth: str, url: str) -> dict:
    """ Makes Spotify non-account request with time/response logging"""
    reqtime = dt.datetime.now()
    req = net.get(url, headers=getheader(oauth)).json())
    if "error" in req:
        errtime = dt.datetime.now()
        with open("net.log", "a+") as err:
            err.write('\n'.join([str(reqtime), str(errtime), url, str(req)]))
            err.write('\n' * 2)
        return req
    return req


def get_playlist(oauth: str, playlist_id: str, limit: int = 512) -> list:
    """ Gets the tracks in a playlist from Spotify
    
    Each track dict includes:
    * `album.album_type` (single, EP, album)
    * `album.artists` (a list of dicts)
    * `album.release_date`
    * `album.release_date_precision` (day, month, year)
    * `artists` (a list of dicts)
    * `id`
    * `linked_from` (only for songs with multiple versions)
    * `name`
    """
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?"
    query = urlparse.urlencode({
        'fields': """
            items(track(
                album(
                    album_type, artists(name, id), release_date,
                    release_date_precision
                ),
                artists(name, id), id, linked_from, name
            ))
        """.replace('\n', '').replace(' ', ''),
        'limit': str(limit)
    }, safe='()', quote_via=urlparse.quote)
    # quote_via=quote avoids pluses if space removal is removed/fails
    return request(oauth, url + query)['items']


# Build this using the generic request function
def get_track(oauth: str, track_id: str) -> dict:
    """ Gets track organizational details

    The dict includes:
    * `album.album_type` (single, EP, album)
    * `album.artists` (a list of dicts)
    * `album.release_date`
    * `album.release_date_precision` (day, month, year)
    * `artists` (a list of dicts)
    * `id`
    * `linked_from` (only for songs with multiple versions)
    * `name`
    """
    url = f"https://api.spotify.com/v1/tracks/{track_id}?"
    query = urlparse.urlencode({
        'fields': """
            album(
                album_type, artists(name, id), release_date,
                release_date_precision
            ),
            artists(name, id), id, linked_from, name
        """.replace('\n', '').replace(' ', ''),
        'limit': str(limit)
    }, safe='()', quote_via=urlparse.quote)
    # quote_via=quote avoids pluses if space removal is removed/fails
    return request(oauth, url + query)


# Enter playlist id to test
def _test(playlist_id: str, debug=True):
    """ playlist can be the URI, URL, or ID """
    playlist_id = playlist_id.replace('spotify:playlist:', '')
    playlist_id = playlist_id.replace('https://open.spotify.com/playlist/', '')
    if '?' in playlist_id:
        playlist_id = playlist_id[0:playlist_id.index('?')]

    with open('APIkeys.json', 'r') as apijson:
        apikeys = json.load(apijson)
    client64 = apikeys['client64']
    oauth = authorize(client64)
    playlist = get_playlist(oauth, playlist_id, 10)
    if debug:
        breakpoint()
    return playlist
