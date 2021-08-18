""" Setup for static type checking and non-trivial casting functions

Copyright (c) 2021 IdmFoundInHim, under MIT License
"""
from __future__ import annotations

__all__ = ['Album', 'Artist', 'Mob', 'Playlist', 'Query', 'Sentence', 'State', 
    'Track']

from collections.abc import Callable, Mapping
from typing import NamedTuple, NewType

from frozendict import frozendict
from spotipy import Spotify


class State(NamedTuple):
    api: Spotify
    mob: Mob
    subshells: frozendict[str, State] = frozendict()


Mob = NewType('Mob', Mapping)
Track = NewType('Track', Mob)
Album = NewType('Album', Mob)
Artist = NewType('Artist', Mob)
Playlist = NewType('Playlist', Mob)

Query = str | Mob
Sentence = Callable[[State, Query], State]
