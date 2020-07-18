import os

CLIENT_ID = "6400ca69c7dd4b969f2620d6d2647b03"
REDIRECT_URI = "http://localhost:8080"
CACHE_PATH = os.path.join('.cache', 'api.json')
MOBNAMES = ['track', 'album', 'artist', 'playlist']
NUMSUGGESTIONS = 3
SCOPE = 'user-library-read user-follow-read'
