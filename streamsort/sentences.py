""" Wrappers for the Spotify API in format f(State, Param) -> State

Copyright (c) 2020 IdmFoundInHim
"""
from itertools import tee, zip_longest
from typing import Any, Callable, Iterator, Optional, Union, cast

from more_itertools import roundrobin
from spotipy import Spotify, SpotifyPKCE

from .cache import liked_songs_cache_check
from .constants import MOB_GET_FUNCTIONS, MOBNAMES, NUMSUGGESTIONS
from .errors import NoResultsError, UnsupportedQueryError, UnsupportedVerbError
from .interaction import confirm_action, notify_user
from .musictypes import Album, Artist, Mob, Playlist, State, Track, str_mob
from .utilities import iter_mob, as_uri, mob_in_mob, results_generator

LIMIT = 50
Query = Union[str, Mob]
TypeSpecificSearch = Callable[[State, str], Optional[Mob]]
MultipleChoiceFunction = Callable[[Iterator[Mob]], Optional[Mob]]

IO_CONFIRM = cast(Callable[[str], bool], confirm_action)
IO_NOTIFY = cast(Callable[[str], None], notify_user)


def io_inject(confirm: Optional[Callable[[str], bool]] = None,
              notify: Optional[Callable[[str], None]] = None):
    """ Replace default I/O with custom functions """
    global IO_CONFIRM # pylint: disable=global-statement
    IO_CONFIRM = confirm or IO_CONFIRM
    global IO_NOTIFY # pylint: disable=global-statement
    IO_NOTIFY = notify or IO_NOTIFY


def ss_open(subject: State, query: Query) -> State:
    """  Return the specified item as a new subject

    If query is a Mob, use that Mob. Otherwise, search Spotify to select
    an item:

    The query is parsed for music object ("mob") tags: playlist, track,
    album, and artist. The first tag of that list that is found is set
    as the desired output type. Playlists are handled differently than
    the other types, while the latter three can be mixed to constrain
    the results.

    >>> sub = ss_open(sub,
    ...    "album:Only Love Remains artist:JJ Heller track:Love Me")
    >>> sub[1]['name']
    'Love Me'
    >>> sub[1]['album']['name']
    'Only Love Remains'

    Playlist search ignores other tags, but may produce strange results
    if other tags are included
    >>> sub = ss_open(sub, "playlist:Star Wars track:Soundtracks")
    >>> sub[1]['owner']['id']
    'khrpgai88r1q1nr12k4f6r2qz'

    To allow quick, adaptive searching, results are prioritized as
    follows:

    Playlist

    0. In Current Subject
    1. Current User Owns
    2. Current User Follows
    3. All Others

    Tracks, Albums, Artists

    0. In Current Subject
    1. Current User Follows artist
       (That is, an artist associated with the track/album)
    2. Current User's Liked Songs Contains
       For albums and artists, only one song from that album/artist
       must be added to Liked Songs
    3. Current User's Liked Songs Contains artist
    4. All Others

    No Tags

    Alternates between Track/Album/Artist and Playlist

    When a selection is made, `IO_NOTIFY` will be called to inform the
    user. For selections with less certainty, `IO_CONFIRM` will be used
    to check with the user before finalizing the selection. Custom I/O
    functions may be supplied through `io_inject`.
    """
    try:
        assert cast(Mob, query)['uri']
        return State(subject.api, cast(Mob, query))
    except (AssertionError, TypeError):
        search_query = cast(str, query)
    out = _ss_open_process_query(search_query)(subject, search_query)
    if out is None:
        raise NoResultsError
    return State(subject.api, out, subject.subshells)


def ss_add(subject: State, query: Query) -> State:
    """ Add all songs in query to the subject (playlist)

    The query will be resolved to a Mob via ss_open. The query is not
    permitted to represent an artist.

    The subject will be returned, pointing to the same mob but updated
    as it will have changed.
    """
    if subject.mob['type'] != 'playlist':
        raise UnsupportedVerbError(str_mob(subject.mob), 'add')
    _ss_add_mob(subject.api, subject.mob,
                ss_open(subject, query).mob)
    return ss_open(subject, subject.mob['uri'])


def ss_remove(subject: State, query: Query) -> State:
    """ Entirely remove all songs in query from the subject (playlist)

    The query will be resolved to a Mob via ss_open. The query is not
    permitted to represent an artist.

    All instances (rather than only the first) of each song will be
    removed from the subject.

    The subject will be returned, pointing to the same mob but updated
    as it will have changed.
    """
    if subject.mob['type'] != 'playlist':
        raise UnsupportedVerbError(str_mob(subject.mob), 'remove')
    _ss_remove_mob(subject.api, subject.mob,
                   ss_open(subject, query).mob)
    return ss_open(subject, subject.mob['uri'])


def ss_play(subject: State, query: Query) -> State:
    to_play = ss_open(subject, query).mob
    if (subject.mob['type'] not in ['track', 'artist']
            and mob_in_mob(subject.api, to_play, subject.mob)):
        _ss_play_in_context(subject.api, subject.mob, to_play)
    else:
        subject.api.start_playback(uris=list(iter_mob(subject.api.auth_manager,
                                                      to_play)))
    return subject


def _ss_open_process_query(query: str) -> TypeSpecificSearch:
    if as_uri(query):
        return _ss_open_uri
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


def _ss_open_uri(subject: State, query: str) -> Optional[Mob]:
    api = subject[0]
    _, mobtype, mobid = as_uri(query).split(':')
    try:
        return MOB_GET_FUNCTIONS[mobtype](api, mobid)
    except KeyError:
        return None


def _ss_open_general(subject: State, query: str) -> Optional[Mob]:
    api = subject[0]
    results = api.search(query, LIMIT, type=','.join(MOBNAMES))
    results = {x: _ss_open_familiar(subject, results[x + 's'], x)
                  if x != 'playlist'
                  else _ss_open_playlist_familiar(subject,
                                                  results['playlists'])
               for x in MOBNAMES}
    for result_gens in roundrobin(*[zip(*[results[t] for t in mobtypes])
                                    for mobtypes
                                    in [MOBNAMES[:-1], MOBNAMES[-1:]]]):
        # Current result_gens: Iterable[Iterator[Iterator[Mob]]]
        # Desired result_gens: Iterable[Iterator[Mob]]
        # priority_results: Iterator[Mob]
        priority_results, pr_original = tee(roundrobin(*result_gens))
        if first_result := next(priority_results, None):
            if next(priority_results, None):
                get_full_object = MOB_GET_FUNCTIONS[first_result['type']]
                return get_full_object(api, first_result['id'])
            if user_select := _ss_open_userinput(pr_original):
                get_full_object = MOB_GET_FUNCTIONS[user_select['type']]
                return get_full_object(api, user_select['id'])
    return None


def _ss_open_playlist(subject: State, query: str) -> Optional[Playlist]:
    api = subject[0]
    results = api.search(query, LIMIT, type='playlist')['playlists']
    results = _ss_open_playlist_familiar(subject, results)
    num_results, results_familiar = _ss_open_genlen(next(results))
    if num_results:
        result = api.playlist(next(results_familiar)['id'])
        return cast(Playlist | None, _ss_open_notifyuser(result))
    results_f1, results_f2 = tee(next(results))
    first_result = next(results_f1, None)
    if first_result and all(z[0] == z[1] for z in zip(first_result['name'],
                                                      query)):
        result = api.playlist(first_result)
        return cast(Playlist | None, _ss_open_notifyuser(result))
    if first_result:
        user_select = _ss_open_userinput(results_f2)
        if user_select:
            return cast(Optional[Playlist], api.playlist(user_select['id']))
    num_results, results_familiar = _ss_open_genlen(next(results))
    if num_results == 1:
        result = api.playlist(next(results_familiar)['id'])
        return cast(Optional[Playlist], _ss_open_notifyuser(result))
    if num_results:
        user_select = _ss_open_userinput(results)
        if user_select:
            return cast(Optional[Playlist], api.playlist(user_select['id']))
    return None


def _ss_open_playlist_familiar(subject: State,
                               results: dict) -> Iterator[Iterator[Playlist]]:
    api = subject[0]
    yield (cast(Playlist, p)
           for p in results_generator(api.auth_manager, results)
           if p['id'] == subject[1]['id'])
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
    def get_track(subject: State, query: str) -> Optional[Track]:
        api = subject[0]
        results = api.search(query, LIMIT, type='track')['tracks']
        results_tiered = _ss_open_familiar(subject, results, MOBNAMES[0])
        for unconfidence, tier in enumerate(results_tiered):
            num_results, results = _ss_open_genlen(tier)
            if num_results == 1 and unconfidence < 3:
                return cast(Track, next(results))
            if num_results:
                user_select = variation(results,)
                # UNREACHED breakpoint()
                if user_select:
                    return cast(Track, user_select)
        # REACHED breakpoint()
        return None

    return get_track


def _ss_open_album(variation: MultipleChoiceFunction) -> TypeSpecificSearch:
    def get_album(subject: State, query: str) -> Optional[Album]:
        api = subject[0]
        results = api.search(query, LIMIT, type='album')['albums']
        results = _ss_open_familiar(subject, results, MOBNAMES[0])
        for unconfidence, results in enumerate(results):
            num_results, results = _ss_open_genlen(results)
            if num_results == 1 and unconfidence < 3:
                return api.album(next(results)['id'])
            if num_results:
                user_select = variation(results,)
                if user_select:
                    return cast(Album, api.album(user_select['id']))
        return None

    return get_album


def _ss_open_artist(variation: MultipleChoiceFunction) -> TypeSpecificSearch:
    def get_artist(subject: State, query: str) -> Optional[Artist]:
        api = subject[0]
        results = api.search(query, LIMIT, type='artist')['artists']
        results = _ss_open_familiar(subject, results, MOBNAMES[0])
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


def _ss_open_genlen(generator: Iterator) -> tuple[int, Iterator]:
    scan_copy, return_copy = tee(generator)
    one_result = next(scan_copy, None)
    if next(scan_copy, None) is not None:
        val = 2
    else:
        val = int(one_result is not None)
    del scan_copy
    return val, return_copy


def _ss_open_familiar(subject: State, results: dict,
                      mobname: str) -> Iterator[Iterator[Mob]]:
    api = subject[0]
    yield (r for r in results_generator(api.auth_manager, results)
           if mob_in_mob(api, r, subject[1]))
    yield (r for r in results_generator(api.auth_manager, results)
           if any(cast(list,
                       api.current_user_following_artists(a['id'] for a
                                                          in r.get('artists',
                                                                   [r])
           )      )     )                                 )
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
        if IO_CONFIRM(f"Continue with {str_mob(suggestion)}?"):
            return suggestion
        if (suggestions_given := suggestions_given + 1) > NUMSUGGESTIONS:
            return None
    return None


def _ss_open_notifyuser(selection: Optional[Mob] = None) -> Optional[Mob]:
    if selection:
        IO_NOTIFY(f"Using {str_mob(selection)}")
        return selection
    IO_NOTIFY("Seach returned no results")
    return None


def _ss_add_mob(api: Spotify, destination: Mob, target: Mob):
    if target['type'] == 'artist':
        raise UnsupportedQueryError('add', str_mob(target))
    api.playlist_add_items(destination['id'],
                           iter_mob(api.auth_manager, target))


def _ss_remove_mob(api: Spotify, destination: Mob, target: Mob):
    if target['type'] == 'artist':
        raise UnsupportedQueryError('remove', str_mob(target))
    api.playlist_remove_all_occurrences_of_items(destination['id'],
                                                 iter_mob(api.auth_manager,
                                                           target))


def _ss_play_in_context(api: Spotify, context: Mob, to_play: Mob):
    context_gen = results_generator(api.auth_manager, context['tracks'])
    for obj in context_gen:
        if mob_in_mob(api, obj.get('track', obj), to_play):
            api.start_playback(context_uri=context['uri'],
                               offset=obj.get('track', obj))
            break


if __name__ == "__main__":
    from .sh import login
    sp, usr, _ = login()
    sub = (sp, None)
    io_inject(lambda x: True)
    import doctest
    doctest.testmod()
