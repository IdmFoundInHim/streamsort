import json
import datetime as dt
from typing import Callable

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
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {oauth}",
    }


# This needs split into a generic request function and playlist-focused
# function. Likely one of these should be a decorator
def get_playlist(oauth: str, playlist_id: str, limit: int = 512):
    url = (f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?"
           "fields=items(track("
           "album(album_type%2Cartists(name%2Cid)"
                   "%2Crelease_date%2Crelease_date_precision)"
           "%2Cartists(name%2Cid)%2Cid%2Clinked_from%2Cname))"
           f"&limit={limit}")
    try:
        reqtime = dt.datetime.now()
        return (req := net.get(url, headers=getheader(oauth)).json())['items']
    except KeyError:
        errtime = dt.datetime.now()
        with open("net.log", "r+") as err:
            err.write('\n'.join(str(reqtime), str(errtime), url, str(req)))
        return req


# Build this using the generic request function
def get_track(oauth: str, track_id: str) -> dict:
    pass


# Enter playlist id to test
def _test(playlist_id, debug=True):
    with open('APIkeys.json', 'r') as apijson:
        apikeys = json.load(apijson)
    client64 = apikeys['client64']
    oauth = authorize(client64)
    breakpoint()
    playlist = get_playlist(oauth, playlist_id, 10)
    if debug:
        breakpoint()
    return playlist
