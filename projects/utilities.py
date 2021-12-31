""" StreamSort Projects Extension -- Utilities Module 

Copyright (c) 2021 IdmFoundInHim, under MIT License
"""
from collections.abc import Sequence
from itertools import zip_longest
from collections.abc import Mapping

from streamsort import mob_eq
from streamsort.types import Mob

from .constants import SINGLE_MAX_MS, SINGLE_MAX_TRACKS


def categorize_projects(
    projects: Sequence[Mapping],
) -> tuple[list[dict], list[dict], list[dict]]:
    project_list = list[dict]()
    singles, albums = list[dict](), list[dict]()
    for project in projects:
        if (
            len(project["objects"]) <= SINGLE_MAX_TRACKS
            and sum(t["duration_ms"] for t in project["objects"])
            <= SINGLE_MAX_MS
        ):
            project = {**project, "length_class": "single"}
            singles.append(project)
        else:
            project = {**project, "length_class": "album"}
            albums.append(project)
        project_list.append(project)
    if len(project_list) and len(albums):
        assert albums[0] is project_list[0] or singles[0] is project_list[0]
    elif len(project_list):
        assert singles[0] is project_list[0]
    return project_list, singles, albums


def song_presumed_eq(song1: Mob, song2: Mob) -> bool:
    return song1["name"] == song2["name"] and all(
        mob_eq(*artists)
        for artists in zip_longest(
            song1["artists"], song2["artists"], fillvalue={"uri": ""}
        )
    )


def single_in_album(single: Mob, album: Mob) -> bool:
    album_tracks = {t["name"]: t["artists"] for t in album["objects"]}
    for track in single["objects"]:
        if not all(
            mob_eq(*artists)
            for artists in zip_longest(
                track["artists"],
                album_tracks.get(track["name"], []),
                fillvalue={"uri": ""},
            )
        ):
            return False
    return True
