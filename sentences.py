""" Wrappers for the Spotify API in format f(Subject, Param) -> Subject

Copyright (c) 2020 IdmFoundInHim
"""
import itertools as itools
from typing import Callable, Iterator, Optional, Tuple, cast

from spotipy import Spotify

from cache import liked_songs_cache_check
from constants import MOBNAMES, NUMSUGGESTIONS
from errors import NoResultsException
from interaction import confirm_action, notify_user
from musictypes import Album, Artist, Mob, Playlist, Track, str_mob
from utilities import results_generator, roundrobin

LIMIT = 50
Subject = Tuple[Spotify, dict]
TypeSpecificSearch = Callable[[Subject, str], Optional[Mob]]
MultipleChoiceFunction = Callable[[Iterator[Mob]], Optional[Mob]]

io_confirm = cast(Callable[[str], bool], confirm_action)
io_notify = cast(Callable[[str], None], notify_user)


def io_inject(confirm: Optional[Callable[[str], bool]] = None,
              notify: Optional[Callable[[str], None]] = None):
    """ Replace default I/O with custom functions """
    global io_confirm # pylint: disable=global-statement,invalid-name
    io_confirm = confirm or io_confirm
    global io_notify # pylint: disable=global-statement,invalid-name
    io_notify = notify or io_notify


def ss_open(subject: Subject, query: str) -> Subject:
    """ Search Spotify and return the selected item as a new subject

    The query is parsed for music object ("mob") tags: playlist, track,
    album, and artist. The first tag of that list that is found is set
    as the desired output type. Playlists are handled differently than
    the other types, while the latter three can be mixed to constrain
    the results.

    >>> sub = ss_open(sub,
    ...    "album:Only Love Remains artist:JJ Heller track:Love Me")
    >>> sub[1]['name']
    Love Me
    >>> sub[1]['album']['name']
    Only Love Remains

    Playlist search ignores other tags, but may produce strange results
    if other tags are included
    >>> sub = ss_open(sub, "playlist:Star Wars track:Soundtracks")
    >>> sub[1]['owner']['id']
    khrpgai88r1q1nr12k4f6r2qz

    To allow quick, adaptive searching, results are prioritized as
    follows:

    Playlist

    1. Current User Owns
    2. Current User Follows
    3. All Others

    Tracks, Albums, Artists

    1. Current User Follows artist
       (That is, an artist associated with the track/album)
    2. Current User's Liked Songs Contains
       For albums and artists, only one song from that album/artist
       must be added to Liked Songs
    3. Current User's Liked Songs Contains artist
    4. All Others

    No Tags

    Alternates between Track/Album/Artist and Playlist
    """
    out = _ss_open_process_query(query)(subject, query)
    if out is None:
        raise NoResultsException
    return (subject[0], out)


def _ss_open_process_query(query: str) -> TypeSpecificSearch:
    tags = {t: (t + ':' in query) for t in MOBNAMES}
    if tags['playlist']:
        return _ss_open_playlist
    if tags['track'] and (tags['album'] or tags['artist']):
        return _ss_open_track(variation=_ss_open_firstresult)
    if tags['track']:
        return _ss_open_track(variation=_ss_open_userinput)
    if tags['album'] and tags['artist']:
        return _ss_open_album(variation=_ss_open_firstresult)
    if tags['album']:
        return _ss_open_album(variation=_ss_open_userinput)
    if tags['artist']:
        return _ss_open_artist(variation=_ss_open_firstresult)
    return _ss_open_general


def _ss_open_general(subject: Subject, query: str) -> Optional[Mob]:
    api = subject[0]
    results = api.search(query, LIMIT, type=','.join(MOBNAMES))
    results = {x: _ss_open_familiar(api.auth_manager, results[x + 's'], x)
                  if x != 'playlist'
                  else _ss_open_playlist_familiar(api, results)
               for x in MOBNAMES}
    for mobtypes in itools.cycle([[x for x in MOBNAMES if x != 'playlist'],
                                  ['playlist']]):
        result_gens = [_ss_open_genlen(next(results[t])) for t in mobtypes]
        num_results = sum(tup[0] for tup in result_gens)
        if num_results == 1:
            return _ss_open_notifyuser(next(roundrobin(*result_gens)))
        if num_results:
            user_select = _ss_open_userinput(roundrobin(*result_gens))
            if user_select:
                return user_select
    return None


def _ss_open_playlist(subject: Subject, query: str) -> Optional[Playlist]:
    api = subject[0]
    results = api.search(query, LIMIT, type='playlist')['playlists']
    results = _ss_open_playlist_familiar(api, results)
    num_results, results_familiar = _ss_open_genlen(next(results))
    if num_results:
        return cast(Optional[Playlist], _ss_open_notifyuser(next(results)))
    results_f1, results_f2 = itools.tee(next(results))
    first_result = next(results_f1, None)
    if first_result and all(z[0] == z[1] for z in zip(first_result['name'],
                                                      query)):
        return cast(Optional[Playlist], _ss_open_notifyuser(first_result))
    if first_result:
        user_select = _ss_open_userinput(results_f2)
        if user_select:
            return cast(Optional[Playlist], user_select)
    num_results, results_familiar = _ss_open_genlen(next(results))
    if num_results == 1:
        return cast(Optional[Playlist],
                    _ss_open_notifyuser(next(results_familiar)))
    if num_results:
        return cast(Optional[Playlist], _ss_open_userinput(results))
    return None


def _ss_open_playlist_familiar(api: Spotify,
                               results: dict) -> Iterator[Iterator[Playlist]]:
    usrid = api.me()['id']
    yield (cast(Playlist, p)
           for p in results_generator(api.auth_manager, results)
           if p['owner']['id'] == usrid)
    yield (cast(Playlist, p)
           for p in results_generator(api.auth_manager, results)
           if api.playlist_is_following(p['id'], [usrid]))
    yield cast(Iterator[Playlist],
               results_generator(api.auth_manager, results))


def _ss_open_track(variation: MultipleChoiceFunction) -> TypeSpecificSearch:
    def get_track(subject: Subject, query: str) -> Optional[Track]:
        api = subject[0]
        results = api.search(query, LIMIT, type='track')['tracks']
        results = _ss_open_familiar(api, results, MOBNAMES[0])
        for unconfidence, results in enumerate(results):
            num_results, results = _ss_open_genlen(results)
            if num_results == 1 and unconfidence < 3:
                return cast(Track, next(results))
            if num_results:
                user_select = variation(results,)
                if user_select:
                    return cast(Track, user_select)
        return None

    return get_track


def _ss_open_album(variation: MultipleChoiceFunction) -> TypeSpecificSearch:
    def get_album(subject: Subject, query: str) -> Optional[Album]:
        api = subject[0]
        results = api.search(query, LIMIT, type='album')['albums']
        results = _ss_open_familiar(api, results, MOBNAMES[0])
        for unconfidence, results in enumerate(results):
            num_results, results = _ss_open_genlen(results)
            if num_results == 1 and unconfidence < 3:
                return next(results)
            if num_results:
                user_select = variation(results,)
                if user_select:
                    return cast(Album, user_select)
        return None

    return get_album


def _ss_open_artist(variation: MultipleChoiceFunction) -> TypeSpecificSearch:
    def get_artist(subject: Subject, query: str) -> Optional[Artist]:
        api = subject[0]
        results = api.search(query, LIMIT, type='artist')['artists']
        results = _ss_open_familiar(api, results, MOBNAMES[0])
        for unconfidence, results in enumerate(results):
            if unconfidence == 2:
                pass
            num_results, results = _ss_open_genlen(results)
            if num_results == 1 and unconfidence < 3:
                return next(results)
            if num_results:
                user_select = variation(results,)
                if user_select:
                    return cast(Artist, user_select)
        return None

    return get_artist


def _ss_open_genlen(generator: Iterator) -> Tuple[int, Iterator]:
    scan_copy, return_copy = itools.tee(generator)
    one_result = next(scan_copy, False)
    if next(scan_copy, False) is not False:
        val = 2
    else:
        val = int(one_result is not False)
    del scan_copy
    return val, return_copy


def _ss_open_familiar(api: Spotify, results: dict,
                      mobname: str) -> Iterator[Iterator[Mob]]:
    yield (r for r in results_generator(api.auth_manager, results)
           if any(api.current_user_following_artists(a['id'] for a
                                                     in r.get('artists', r))))
    liked_songs = liked_songs_cache_check(api)
    yield (r for r in results_generator(api.auth_manager, results)
           if r['id'] in liked_songs[mobname])
    yield (r for r in results_generator(api.auth_manager, results)
           if any(a in liked_songs['artist']
                  for a in r.get('artists') or [r['id']]))
    yield results_generator(api.auth_manager, results)


def _ss_open_firstresult(results: Iterator[Mob]) -> Mob:
    return cast(Mob, _ss_open_notifyuser(next(results)))


def _ss_open_userinput(results: Iterator[Mob]) -> Optional[Mob]:
    suggestions_given = 0
    for suggestion in results:
        if io_confirm(f"Continue with {str_mob(suggestion)}?"):
            return suggestion
        if (suggestions_given := suggestions_given + 1) > NUMSUGGESTIONS:
            return None
    return None


def _ss_open_notifyuser(selection: Optional[Mob] = None) -> Optional[Mob]:
    if selection:
        io_notify(f"Using {str_mob(selection)}")
        return selection
    io_notify("Seach returned no results")
    return None


if __name__ == "__main__":
    import sh
    sp, usr = sh.login()
    sub = (sp, None)
    import doctest
    doctest.testmod()
