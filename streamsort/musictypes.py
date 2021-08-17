""" Setup for static type checking and non-trivial casting functions

Copyright (c) 2021 IdmFoundInHim, under MIT License
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import NamedTuple, NewType

from frozendict import frozendict
from spotipy import Spotify

Mob = NewType('Mob', Mapping)
Track = NewType('Track', Mob)
Album = NewType('Album', Mob)
Artist = NewType('Artist', Mob)
Playlist = NewType('Playlist', Mob)


_MOB_STRS = {
    'track': '"{}" by {}{}',
    'album': '*{}* by {}, {} songs',
    'artist': '{}{}{}',
    'playlist': '{}, {}{} songs',
    'episode': '"{}" from *{}{}*',
    'show': '*{}* from {}{}',
    'user': '@{}{}{}',
    'ss': ':{}{}{}'
}


def str_mob(mob: Mob):
    """ Constructs display string of given Mob (dict) """
    mob_fields = [mob.get('name', mob.get('display_name')),
                  mob['artists'][0]['name'] if mob.get('artists')
                    else mob.get('show', mob.get('publisher', '')),
                  mob.get('total_tracks')
                    or mob['tracks']['total'] if mob.get('tracks')
                    else mob['episodes']['total'] if mob.get('episodes')
                    else '']
    return _MOB_STRS[mob['type']].format(*mob_fields)


class State(NamedTuple):
    api: Spotify
    mob: Mob
    subshells: frozendict[str, State] = frozendict()
