""" Package-level Constants for StreamSort

Copyright (c) 2021 IdmFoundInHim, under MIT License
"""
__all__ = ['CLIENT_ID', 'REDIRECT_URI', 'CACHE_DIR', 'CACHE_PATH',
    'MOB_URI_PREFIX', 'MOB_URL_PREFIX', 'SPID_VALID_CHARS', 'SPID_VALID_CHARS',
    'MOBNAMES', 'MOB_GET_FUNCTIONS', 'NUMSUGGESTIONS', 'SCOPE']

import os
import string

from spotipy import Spotify

CLIENT_ID = "6400ca69c7dd4b969f2620d6d2647b03"
REDIRECT_URI = "http://localhost:8080"
CACHE_DIR = '.cache'
CACHE_PATH = os.path.join(CACHE_DIR, 'api.json')
MOB_URI_PREFIX = 'spotify:'
MOB_URL_PREFIX = 'https://open.spotify.com/'
SPID_VALID_CHARS = string.ascii_letters + string.digits
MOBNAMES = ['track', 'album', 'artist', 'playlist']
MOB_GET_FUNCTIONS = {
    'track': Spotify.track,
    'album': Spotify.album,
    'artist': Spotify.artist,
    'playlist': Spotify.playlist,
    'episode': Spotify.episode,
    'show': Spotify.show,
    'user': Spotify.user
}
NUMSUGGESTIONS = 3
SCOPE = ('user-library-read user-follow-read playlist-read-private '
         + 'playlist-modify-private playlist-modify-public '
         + 'user-modify-playback-state')
EXTENSION_ATTRIBUTE = '_sentences_'
