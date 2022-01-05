""" StreamSort Shuffle Extension -- Sentences Module 

Copyright (c) 2021 IdmFoundInHim, under MIT License
"""
__all__ = ["ss_shuffle"]

import random
from typing import cast

from spotipy import SpotifyPKCE
from streamsort import (
    UnsupportedQueryError,
    UnsupportedVerbError,
    results_generator,
    ss_add,
    ss_new,
    ss_open,
    ss_remove,
    str_mob,
)
from streamsort.types import Mob, Query, State


def ss_shuffle(subject: State, query: Query):
    """(ALPHA: Behavior subject to change) Shuffle a list of mobs

    Currently uploads result of shuffling the subject to the queried
    playlist.

    Only shuffles the topmost layer of an SS Object, allowing groups
    of tracks to stay together depending on the construction of the
    subject.
    """
    verb_error = UnsupportedVerbError(str_mob(subject.mob), "shuffle")
    query_error = UnsupportedQueryError(
        "shuffle", query if isinstance(query, str) else str_mob(query)
    )
    try:
        if not query:
            query = subject.mob
            subject = ss_new(subject, "Shuffled: " + subject.mob["name"])
        else:
            query = ss_open(subject, query).mob
    except KeyError:
        raise query_error
        # raise UnsupportedQueryError('The query was empty and the subject '
        #                             'was not list-like'
    try:
        if query.get("tracks"):
            playlist = list(
                results_generator(
                    cast(SpotifyPKCE, subject.api.auth_manager),
                    query["tracks"],
                )
            )
        else:
            playlist = query["objects"]
    except KeyError:
        raise query_error
        # raise UnsupportedQueryError('The query was not list-like')
    random.shuffle(playlist)
    try:
        ss_remove(subject, subject.mob)
        ss_add(subject, Mob({"objects": playlist, "type": "ss"}))
    except UnsupportedVerbError as err:
        raise verb_error from err
        # raise UnsupportedVerbError('The subject was not editable') from err
    return ss_open(subject, subject.mob["uri"])
