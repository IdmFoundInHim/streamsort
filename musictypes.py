from typing import NewType, List
from string import digits, ascii_letters
from requests import HTTPError

import api

SpID = NewType('SpID', str)
Track = NewType('Track', SpID)
AlbumID = NewType('AlbumID', SpID)
ArtistID = NewType('ArtistID', SpID)
PlaylistID = NewType('PlaylistID', SpID) 
# PlaylistID always points to a Songlist
# Local playlists can contain custom identifiers (like projects)
Songlist = NewType('Songlist', List)

TYPENAMES = ['track', 'album', 'artist', 'playlist']
# This is the preferred order for this list due to sentences > ss_get
TYPEMAPS = {
    'track': Track,
    'album': AlbumID,
    'artist': ArtistID,
    'playlist': PlaylistID,
    0: Track,
    1: AlbumID,
    2: ArtistID,
    3: PlaylistID
}

def validate_spid_format(spid: str) -> SpID:
    if len(spid) != 22:
        return ''
    for c in spid:
        if c not in ascii_letters and c not in digits:
            return ''
    return SpID(spid)


def derive_spid(identifier: str) -> SpID:
    """ Extract Spotify ID from URI or URL """
    if 'spotify:' not in identifier and 'spotify.com' not in identifier:
        return validate_spid_format(identifier)
    identifier = identifier.split('/')[-1]
    identifier = identifier.split(':')[-1]
    if '?' in identifier:
        return identifier[0:identifier.index('?')]
    return validate_spid_format(identifier)


def validate_track(track: SpID) -> Track:
    try:
        api.request_get(api.auth_localtoken(),
                        f"https://open.spotify.com/api/v1/tracks/{track}", '')
        return Track(track)
    except HTTPError:
        return ''


def validate_albumid(album_id: SpID) -> AlbumID:
    try:
        api.request_get(api.auth_localtoken(), "https://open.spotify.com/api/"
                        f"v1/albums/{album_id}", '')
        return AlbumID(album_id)
    except HTTPError:
        return ''


def validate_artistid(artist_id: SpID) -> ArtistID:
    try:
        api.request_get(api.auth_localtoken(), "https://open.spotify.com/api/"
                        f"v1/artists/{artist_id}", '')
        return ArtistID(artist_id)
    except HTTPError:
        return ''

def validate_playlistid(playlist_id: SpID) -> ArtistID:
    try:
        api.request_get(api.auth_localtoken(), "https://open.spotify.com/api/"
                        f"v1/playlists/{playlist_id}", '')
        return PlaylistID(playlist_id)
    except HTTPError:
        return ''

def validate_songlist(list_songs: List) -> Songlist:
    for song in list_songs:
        if validate_spid_format(song) and validate_track(song):
            pass
        else:
            return []