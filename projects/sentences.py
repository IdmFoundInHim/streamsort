""" StreamSort Projects Extension -- Sentences Module 

Copyright (c) 2021 IdmFoundInHim, under MIT License
"""
__all__ = ["ss_projects"]

from collections.abc import Iterable
from typing import Sequence, cast

from frozendict import frozendict
from spotipy import Spotify, SpotifyPKCE
from streamsort import (
    SimplifiedObjectError,
    iter_mob_track,
    results_generator,
    ss_open,
)
from streamsort.types import Mob, Query, State

from .utilities import categorize_projects, single_in_album


def ss_projects(subject: State, query: Query) -> State:
    """Split a list-like mob by release format (album/single)"""
    if not query:
        query = subject.mob
    api = subject.api
    query_mob = ss_open(subject, query).mob
    print('    NOTE: "projects" may take a while')
    tracks = list(
        iter_mob_track(cast(SpotifyPKCE, api.auth_manager), query_mob)
    )
    try:
        projects_prefilter = _divide(tracks)
    except SimplifiedObjectError:
        projects_prefilter = _divide(
            cast(Mob, subject.api.track(t["uri"])) for t in tracks
        )
    projects = _filter_singles(subject.api, projects_prefilter)
    out_mob = {
        "type": "ss",
        "name": f"Projects: {query_mob['name']}",
        "objects": projects,
    }  # needs 'details' key when display format is finalized
    return State(api, Mob(frozendict(out_mob)), subject[2])


def _divide(tracks: Iterable[Mob]) -> list[dict]:
    albums = {}
    for track in tracks:
        try:
            album_id: str = track["album"]["id"]
        except KeyError:
            raise SimplifiedObjectError
        if existing_album := albums.get(album_id):
            albums[album_id]["objects"] = existing_album["objects"] + [track]
        else:
            albums[album_id] = {
                "type": "ss",
                "name": track["album"]["name"],
                "root_album": track["album"],
                # Add? # 'artists': track['album']['artists']
                "objects": [track],
            }
    return list(albums.values())


def _filter_singles(api: Spotify, projects: Sequence[dict]) -> list[Mob]:
    for project in projects:
        # Remove duplicates and put in order
        project_ids = [t["id"] for t in project["objects"]]
        # Adding the following check assumes that projects are in order.
        # It speeds up processing of playlists with few duplicates (that
        # is, most practical use cases) by ~20x. This optimization has
        # been excluded for potential usage on shuffled lists.
        # --------------------------------------------------------------
        # if len(project["objects"]) != len(
        #     set(t["uri"] for t in project["objects"])
        # ):
        try:
            project["objects"] = [
                t
                for t in results_generator(
                    cast(SpotifyPKCE, api.auth_manager),
                    cast(
                        dict,
                        api.album_tracks(project["root_album"]["uri"]),
                    ),
                )
                if t["id"] in project_ids
            ]
        except AttributeError:
            pass
    project_list, singles, albums = categorize_projects(projects)
    for single in singles:
        for album in albums:
            if single_in_album(cast(Mob, single), cast(Mob, album)):
                project_list.remove(single)
    return [Mob(frozendict(d)) for d in project_list]
