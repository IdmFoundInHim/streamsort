import os
import string

from spotipy import Spotify

CLIENT_ID = "6400ca69c7dd4b969f2620d6d2647b03"
REDIRECT_URI = "http://localhost:8080"
CACHE_PATH = os.path.join('.cache', 'api.json')
MOB_URI_PREFIX = 'spotify:'
MOB_URL_PREFIX = 'https://open.spotify.com/'
SPID_VALID_CHARS = string.ascii_letters + string.digits
MOBNAMES = ['track', 'album', 'artist', 'playlist']
MOB_GET_FUNCTIONS = {
    'track': Spotify.track,
    'album': Spotify.album,
    'artist': Spotify.artist,
    'playlist': Spotify.playlist
}
NUMSUGGESTIONS = 3
SCOPE = ('user-library-read user-follow-read playlist-read-private '
         'playlist-modify-private playlist-modify-public')
