from typing import NewType

Mob = NewType('Mob', dict)
Track = NewType('Track', Mob)
Album = NewType('Album', Mob)
Artist = NewType('Artist', Mob)
Playlist = NewType('Playlist', Mob)


def str_mob(mob: Mob):
    mob_strs = {
        'track': '"{}" by {}{}',
        'album': '*{}* by {}, {} songs',
        'artist': '{}{}{}',
        'playlist': '{}, {}{} songs'
    }
    mob_fields = [mob['name'],
                  (mob.get('artists', [0])[0] or {'name': ''})['name'],
                  len(mob.get('items', [])) or '']
    return mob_strs[mob['type']].format(*mob_fields)
