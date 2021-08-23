""" StreamSort Projects Extension -- Sentences Module 

Copyright (c) 2021 IdmFoundInHim, under MIT License
"""
__all__ = ["proj_projects"]

from collections.abc import Iterable
from typing import Sequence, cast
from streamsort import results_generator
from .utilities import categorize_projects, single_in_album

from frozendict import frozendict
from spotipy import Spotify
from streamsort import iter_mob_track, ss_open
from streamsort.types import Mob, Query, State


def proj_projects(subject: State, query: Query) -> State:
    if not query:
        query = subject.mob
    api = subject.api
    query_mob = ss_open(subject, query).mob
    print('    NOTE: "projects" may take a while')
    tracks = iter_mob_track(api.auth_manager, query_mob)
    projects_prefilter = _proj_projects_divide(tracks)
    projects = _proj_projects_filter_singles(subject.api, projects_prefilter)
    out_mob = {
        "type": "ss",
        "name": f"Projects: {query_mob['name']}",
        "objects": projects,
    }  # needs 'details' key when display format is finalized
    return State(api, Mob(frozendict(out_mob)), subject[2])


def _proj_projects_divide(tracks: Iterable[Mob]) -> list[dict]:
    albums = {}
    for track in tracks:
        album_id: str = track["album"]["id"]
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


def _proj_projects_filter_singles(
    api: Spotify, projects: Sequence[dict]
) -> list[Mob]:
    for project in projects:
        project_ids = [t["id"] for t in project["objects"]]
        if len(project["objects"]) != len(
            set(t["uri"] for t in project["objects"])
        ):
            # Remove duplicates, ensuring that project ends up in order
            project["objects"] = [
                t
                for t in results_generator(
                    api.auth_manager,
                    cast(str, api.album_tracks(project["root_album"]["id"])),
                )
                if t["id"] in project_ids
            ]
    project_list, singles, albums = categorize_projects(projects)
    for single in singles:
        for album in albums:
            if single_in_album(cast(Mob, single), cast(Mob, album)):
                project_list.remove(single)
    return [Mob(frozendict(d)) for d in project_list]
