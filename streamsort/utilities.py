""" StreamSort utility functions

Copyright (c) 2020 IdmFoundInHim, except where otherwise credited
"""
__all__ = [
    "as_uri",
    "get_header",
    "iter_mob",
    "mob_eq",
    "mob_in_mob",
    "results_generator",
    "str_mob",
]

from collections.abc import Iterator, Mapping
from urllib import parse as urlparse

from more_itertools import flatten
import requests
from spotipy import Spotify, SpotifyPKCE

from ._constants import (
    MOBNAMES,
    MOB_URI_PREFIX,
    MOB_URL_PREFIX,
    SPID_VALID_CHARS,
)
from .types import Mob


def get_header(oauth: str) -> dict:
    """Returns header with given oauth for the Spotify API"""
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {oauth}",
    }


def results_generator(auth: SpotifyPKCE, page_zero: Mapping) -> Iterator[Mob]:
    """Iterates over multi-page responses from Spotify

    If items are being removed or reordered, convert to a list or set.
    Otherwise, songs will be skipped. (The iterator makes API requests
    lazily, always moving the offset by 100. If items are removed before
    the next request is made, the next unused item may be in a position
    less than +100, but the iterator will still get whatever item is in
    position +100.)
    """
    try:
        yield from page_zero["items"]
        if not page_zero["next"]:
            # Included seperately from loop condition because it avoids
            # unnecessary token access (and undesired indentation)
            return
    except KeyError as err:
        raise ValueError("DEVELOPER: Expected paging object") from err
    page = page_zero
    header = get_header(auth.get_access_token())
    while nexturl := page["next"]:
        try:
            page_r = requests.get(nexturl, headers=header)
            page_r.raise_for_status()
            page = page_r.json()
            yield from page["items"]
        except requests.exceptions.HTTPError:
            if "offset=1000" in nexturl:
                return
            header = get_header(auth.get_access_token(check_cache=False))
            page = {"next": nexturl}
        except KeyError:
            key = next((n + "s" for n in MOBNAMES if n + "s" in page), "items")
            page = page[key]
            yield from page["items"]


def as_uri(uri: str):
    """Returns the URI in standard format only if present"""
    if uri.startswith(MOB_URL_PREFIX):
        try:
            url = urlparse.urlparse(uri)
        except ValueError:
            return ""
        uri = MOB_URI_PREFIX + ":".join(url.path.split("/")[-2:])
    uri_parts = uri.strip().split(":")
    if (
        len(uri_parts) == 3
        and uri_parts[0] == "spotify"
        and uri_parts[1] in MOBNAMES
        and all(c in SPID_VALID_CHARS for c in uri_parts[2])
    ):
        return uri
    return ""


def _track_in_mob(auth: SpotifyPKCE, track: Mob, mob: Mob) -> bool:
    if mob["type"] == "artist":
        return mob["uri"] in (a["uri"] for a in track["artists"])
    if mob["type"] == "album":
        return track["uri"] in (
            t["uri"] for t in results_generator(auth, mob["tracks"])
        )
    if mob["type"] == "playlist":
        return track["uri"] in (
            t["track"]["uri"] for t in results_generator(auth, mob["tracks"])
        )
    return False


def _album_in_mob(auth: SpotifyPKCE, album: Mob, mob: Mob) -> bool:
    if mob["type"] == "artist":
        return mob["uri"] in (a["uri"] for a in album["artists"])
    if mob["type"] == "playlist":
        return album["uri"] in (
            t["track"]["album"]["uri"]
            for t in results_generator(auth, mob["tracks"])
        )
    return False


def _artist_in_mob(auth: SpotifyPKCE, artist: Mob, mob: Mob) -> bool:
    if mob["type"] == "track":
        return artist["uri"] in (a["uri"] for a in mob["artists"])
    if mob["type"] == "album":
        return artist["uri"] in (
            a["uri"]
            for a in flatten(
                t["artists"] for t in results_generator(auth, mob["tracks"])
            )
        )
    if mob["type"] == "playlist":
        return artist["uri"] in (
            a["uri"]
            for a in flatten(
                t["track"]["artists"]
                for t in results_generator(auth, mob["tracks"])
            )
        )
    return False


def _playlist_in_playlist(auth: SpotifyPKCE, sub: Mob, lst: Mob) -> bool:
    if lst["type"] != "playlist":
        return False
    lst_gen = (o["track"] for o in results_generator(auth, lst["tracks"]))
    sub_gen = (o["track"] for o in results_generator(auth, sub["tracks"]))
    sub_gen_first = next(sub_gen, {"uri": None})["uri"]
    for track in lst_gen:
        if track["uri"] == sub_gen_first:
            break
    for track in sub_gen:
        if next(lst_gen, {"uri": None})["uri"] != track["uri"]:
            return False
    return True


_MOB_SPECIFIC_TESTS = {
    "track": _track_in_mob,
    "album": _album_in_mob,
    "artist": _artist_in_mob,
    "playlist": _playlist_in_playlist,
}


def mob_in_mob(api: Spotify, obj: Mob, lst: Mob) -> bool:
    """Check if a mob is found in another mob

    All items contain themselves in addition to anything else.
    Albums are considered to contain their tracks + any
    artists credited on those tracks. Artists are considered to contain
    any tracks they are credited on + any albums or playlists
    containing their tracks. Playlists contain their tracks + any
    albums and artists represented in those tracks.

    TODO doctests here

    Episodes match nothing, but throw no error.

    TODO that especially needs doctesting
    """
    if obj.get("uri", None) == lst.get("uri", False):
        return True
    if test := _MOB_SPECIFIC_TESTS.get(obj["type"]):
        return test(api.auth_manager, obj, lst)
    return False


def iter_mob(
    auth: SpotifyPKCE, mob: Mob, keep_local: bool = True
) -> Iterator[str]:
    if objects := mob.get("objects"):
        for obj in objects:
            yield from iter_mob(auth, obj, keep_local)
        return
    if tracks := mob.get("tracks", mob.get("episodes")):
        mob_tracks = results_generator(auth, tracks)
    else:
        mob_tracks = [mob]
    mob_tracks = (t.get("track", t) for t in mob_tracks)
    yield from (
        t["uri"]
        for t in mob_tracks
        if keep_local or t.get("uri", "").startswith("spotify:track:")
    )


_MOB_STRS = {
    "track": '"{}" by {}{}',
    "album": "*{}* by {}, {} songs",
    "artist": "{}{}{}",
    "playlist": "{}, {}{} songs",
    "episode": '"{}" from *{}{}*',
    "show": "*{}* from {}{}",
    "user": "@{}{}{}",
    "ss": ":{}{}{}",
}


def str_mob(mob: Mob):
    """Constructs display string of given Mob (dict)"""
    mob_fields = [
        mob.get("name", mob.get("display_name")),
        mob["artists"][0]["name"]
        if mob.get("artists")
        else mob.get("show", mob.get("publisher", "")),
        mob.get("total_tracks") or mob["tracks"]["total"]
        if mob.get("tracks")
        else mob["episodes"]["total"]
        if mob.get("episodes")
        else "",
    ]
    return _MOB_STRS[mob["type"]].format(*mob_fields)


def mob_eq(mob1: Mob, mob2: Mob) -> bool:
    try:
        return mob1["uri"] == mob2["uri"]
    except KeyError:
        return _ss_eq(mob1, mob2)


def _ss_eq(ss1: Mob, ss2: Mob) -> bool:
    try:
        ss1_objects, ss2_objects = ss1["objects"], ss2["objects"]
    except KeyError as err:
        raise ValueError("DEVELOPER: SS Object needs 'objects' key") from err
    for obj in ss1_objects:
        if uri := obj.get("uri"):
            if uri not in (o.get("uri") for o in ss2_objects):
                return False
        elif obj.get("objects"):
            if not any(
                _ss_eq(obj, o) for o in ss2_objects if o.get("objects")
            ):
                return False
        else:
            raise ValueError("DEVELOPER: SS Object contained invalid objects")
    return True
