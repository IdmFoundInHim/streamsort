""" StreamSort Projects Extension -- Sentences Module 

Copyright (c) 2021 IdmFoundInHim, under MIT License
"""
__all__ = ["proj_projects"]

from typing import cast

from frozendict import frozendict
from streamsort import iter_mob, results_generator, ss_open
from streamsort.types import Mob, Query, State


def proj_projects(subject: State, query: Query) -> State:
    api = subject.api
    query_mob = ss_open(subject, query).mob
    print('    NOTE: "projects" may take a while')
    tracks = (
        cast(dict, api.track(t)) for t in iter_mob(api.auth_manager, query_mob)
    )
    albums = {}
    album_names = {}
    for track in tracks:
        album_id = track["album"]["id"]
        if not album_names.get(album_id):
            album_names[album_id] = track["album"]["name"]
        albums[album_id] = albums.get(album_id, []) + [track]
    single_mappings = {}
    for project in albums:
        for track in albums[project]:
            candidates = results_generator(
                api.auth_manager,
                cast(
                    dict[str, dict],
                    api.search(
                        f"artist:{track['artists'][0]['name']} "
                        f"track:{track['name']}",
                        type="track",
                    ),
                )["tracks"],
            )
            single_mappings[project] = single_mappings.get(project, {})
            single_mappings[project][track["id"]] = [
                t["id"]
                for t in candidates
                if t["name"] == track["name"] and t["album"]["id"] != project
            ]
    projects = [
        frozendict(
            {
                "type": "ss",
                "name": album_names[k],
                "objects": albums[k],
                "singles": single_mappings[k],
                "album_spotify_id": k,
                "album_spotify_uri": f"spotify:album:{k}",
            }
        )
        for k in albums
    ]
    return State(
        api,
        Mob(
            frozendict(
                {
                    "type": "ss",
                    "name": f"Projects: {query_mob['name']}",
                    "objects": projects,
                }
            )
        ),
        subject[2],
    )  # needs 'details' key when display format is finalized
