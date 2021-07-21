""" Setup for static type checking and non-trivial casting functions

Copyright (c) 2020 IdmFoundInHim
"""

from __future__ import annotations
from typing import NamedTuple, NewType

from spotipy import Spotify

from .errors import UnexpectedResponseException

Mob = NewType('Mob', dict)
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
    'show': '*{}* from {}{}'
}


def str_mob(mob: Mob):
    """ Constructs display string of given Mob (dict) """
    mob_fields = [mob['name'],
                  mob['artists'][0]['name'] if mob.get('artists')
                    else mob.get('show', mob.get('publisher')),
                  mob.get('total_tracks')
                    or mob['tracks']['total'] if mob.get('tracks')
                    else mob['episodes']['total'] if mob.get('episodes')
                    else '']
    return _MOB_STRS[mob['type']].format(*mob_fields)


class State(NamedTuple):
    api: Spotify
    mob: Mob
    subshells: dict[str, State] = {}

    def __str__(self):
        mob = self.mob
        assert isinstance(mob, dict)
        try:
            return mob.get('name',
                        mob.get('display_name',
                                mob.get('id', mob['href'])))
        except KeyError as err:
            raise UnexpectedResponseException from err
