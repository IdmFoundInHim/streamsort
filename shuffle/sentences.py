""" StreamSort Shuffle Extension -- Sentences Module 

Copyright (c) 2021 IdmFoundInHim, under MIT License
"""
__all__ = ['shuf_shuffle']

import random

from streamsort import (UnsupportedVerbError, results_generator, ss_add,
                        ss_open, ss_remove, str_mob)
from streamsort.types import Mob, Query, State


def shuf_shuffle(subject: State, query: Query):
    """ (ALPHA: Behavior subject to change) Shuffle a list of mobs

    Currently uploads result of shuffling the subject to the queried
    playlist.

    Only shuffles the topmost layer of an SS Object, allowing groups
    of tracks to stay together depending on the construction of the
    subject.
    """
    try:
        playlist = list(results_generator(subject.api.auth_manager,
            subject.mob['tracks'])
            if subject.mob.get('tracks')
            else subject.mob.get('objects', [subject.mob['id']])
        )
    except KeyError:
        raise UnsupportedVerbError(str_mob(subject.mob), 'shuffle')
    random.shuffle(playlist)
    targeted_playlist = ss_open(subject, query).mob
    local_state = State(subject.api, targeted_playlist)
    ss_remove(local_state, targeted_playlist)
    ss_add(local_state, Mob({'objects': playlist, 'type': 'ss'}))
    return ss_open(subject, targeted_playlist['uri'])
