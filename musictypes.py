""" Setup for static type checking and non-trivial casting functions

Copyright (c) 2020 IdmFoundInHim
"""

from typing import NewType

Mob = NewType('Mob', dict)
Track = NewType('Track', Mob)
Album = NewType('Album', Mob)
Artist = NewType('Artist', Mob)
Playlist = NewType('Playlist', Mob)


def str_mob(mob: Mob):
    """ Constructs display string of given Mob (dict) """
    mob_strs = {
        'track': '"{}" by {}{}',
        'album': '*{}* by {}, {} songs',
        'artist': '{}{}{}',
        'playlist': '{}, {}{} songs'
    }
    mob_fields = [mob['name'],
                  mob.get('artists', [{'name': ''}])[0]['name'],
                  len(mob.get('items', []))
                  or mob.get('tracks', {'total': ''})['total']]
    return mob_strs[mob['type']].format(*mob_fields)
