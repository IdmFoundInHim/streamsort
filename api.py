import json
# from typing import

import requests


def authorize(client64: str) -> str:
    """ Get OAuth key for requests to server.

    If a valid, curretn OAuth key is stored locally in ./APIstate.json
    , it will be retrieved. Otherwise, a request to the server will be
    made with client64 ("{clientid}:{client_secret}" encoded in Base64)
    for a new OAuth key. This will be stored with a timeout value in
    ./APIstate.json, and the OAuth will be returned.
    """
    # INSERT read APIstate.json for authkey and return if not timed out
    header = {
        "Authorization": f"Basic {client64}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = "grant_type=client_credentials"
    oauth = requests.post("https://accounts.spotify.com/api/token",
                          headers=header, data=data)
    # INSERT write to APIstate.json
    return oauth.json()['access_token']


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
    playlist = getplaylist(oauth, playlist_id, 10)
    if debug:
        breakpoint()
    return playlist
