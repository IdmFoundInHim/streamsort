import json
import datetime as dt
# from typing import

import requests


def is_oauth(oauth):
    return type(oauth) is str and len(oauth) == 83

def authorize(client64: str) -> str:
    """ Get OAuth key for requests to server.

    If a valid, curretn OAuth key is stored locally in ./APIstate.json
    , it will be retrieved. Otherwise, a request to the server will be
    made with client64 ("{clientid}:{client_secret}" encoded in Base64)
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
        and is_oauth(oauth := localdict['oauth'])) :
        return oauth
    header = {
        "Authorization": f"Basic {client64}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = "grant_type=client_credentials"
    requesttime = dt.datetime.now()
    oauth = requests.post("https://accounts.spotify.com/api/token",
                          headers=header, data=data).json()
    timeout = requesttime + dt.timedelta(seconds=int(oauth['expires_in']))
    customjson = {
        'oauth': (oauthkey := oauth['access_token']),
        'timeout': timeout.isoformat()
    }
    with open("APIstate.json", 'w') as local:
        json.dump(customjson, local) 
    return oauthkey


def getplaylist(oauth: str, playlist_id: str, limit: int = 512) -> dict:
    header = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {oauth}",
    }
    playlist = requests.get("https://api.spotify.com/v1/playlists/"
                            f"{playlist_id}/tracks?fields=items(track(album"
                            "(artists%2Cname%2Crelease_date)%2Cname%2Cid))&"
                            f"limit={limit}", headers=header)
    return playlist.json()


# Enter playlist id to test
def _test(playlist_id, debug=True):
    with open('APIkeys.json', 'r') as apijson:
        apikeys = json.load(apijson)
    client64 = apikeys['client64']
    oauth = authorize(client64)
    breakpoint()
    playlist = getplaylist(oauth, playlist_id, 10)
    if debug:
        breakpoint()
    return playlist
