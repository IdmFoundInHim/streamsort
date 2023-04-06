""" Wrappers for the Spotify API in format f(State, Param) -> State

Copyright (c) 2021 IdmFoundInHim, under MIT License
"""
__all__ = [
    "io_inject",
    "IO_CONFIRM",
    "IO_NOTIFY",
    "ss_add",
    "ss_all",
    "ss_new",
    "ss_open",
    "ss_play",
    "ss_remove",
]

from collections.abc import Callable, Iterator, Mapping
from itertools import tee
from typing import cast

from frozendict import frozendict
from more_itertools import chunked, roundrobin
from spotipy import Spotify, SpotifyPKCE

from ._cache import liked_songs_cache_check
from ._constants import MOB_GET_FUNCTIONS, MOBNAMES, NUMSUGGESTIONS
from .errors import NoResultsError, UnsupportedQueryError, UnsupportedVerbError
from ._io import confirm_action, notify_user
from .types import Album, Artist, Mob, Playlist, State, Track, Query
from .utilities import (
    as_uri,
    iter_mob_uri,
    mob_eq,
    mob_in_mob,
    results_generator,
    str_mob,
)

LIMIT = 50
TypeSpecificSearch = Callable[[State, str], Mob | None]
MultipleChoiceFunction = Callable[[Iterator[Mob]], Mob | None]

IO_CONFIRM = cast(Callable[[str], bool], confirm_action)
IO_NOTIFY = cast(Callable[[str], None], notify_user)


def io_inject(
    confirm: Callable[[str], bool] | None = None,
    notify: Callable[[str], None] | None = None,
):
    """Replace default I/O with custom functions"""
    global IO_CONFIRM  # pylint: disable=global-statement
    IO_CONFIRM = confirm or IO_CONFIRM
    global IO_NOTIFY  # pylint: disable=global-statement
    IO_NOTIFY = notify or IO_NOTIFY


def ss_open(subject: State, query: Query) -> State:
    """Return the specified item as a new subject

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
    if not query:
        return State(subject[0], cast(Mob, subject.api.me()), subject[2])
    if isinstance(query, Mapping):
        return State(subject[0], query, subject[2])
    search_query = cast(str, query)
    out = _ss_open_process_query(search_query)(subject, search_query)
    if out is None:
        raise NoResultsError
    return State(subject[0], out, subject[2])


def ss_add(subject: State, query: Query) -> State:
    """Add all songs in query to the subject (playlist)

    The query will be resolved to a Mob via ss_open. The query is not
    permitted to represent an artist.

    The subject will be returned, pointing to the same mob but updated
    as it will have changed.
    """
    if not query:
        # raise UnsupportedQueryError('"add" requires a query')
        raise UnsupportedQueryError("add", "")
    if subject.mob["type"] == "playlist":
        _ss_add_to_playlist(
            subject.api, subject.mob, ss_open(subject, query).mob
        )
        return ss_open(subject, subject.mob["uri"])
    elif subject.mob.get("objects") is not None:
        return ss_open(
            subject, _ss_add_to_ss(subject.mob, ss_open(subject, query).mob)
        )
    else:
        raise UnsupportedVerbError(str_mob(subject.mob), "add")


def ss_remove(subject: State, query: Query) -> State:
    """Entirely remove all songs in query from the subject (playlist)

    The query will be resolved to a Mob via ss_open. The query is not
    permitted to represent an artist.

    All instances (rather than only the first) of each song will be
    removed from the subject.

    The subject will be returned, pointing to the same mob but updated
    as it will have changed.
    """
    if not query:
        # raise UnsupportedQueryError('"remove" requires a query')
        raise UnsupportedQueryError("remove", "")
    if subject.mob["type"] == "playlist":
        _ss_remove_from_playlist(
            subject.api, subject.mob, ss_open(subject, query).mob
        )
        return ss_open(subject, subject.mob["uri"])
    elif subject.mob.get("objects") is not None:
        return ss_open(
            subject,
            _ss_remove_from_ss(subject.mob, ss_open(subject, query).mob),
        )
    else:
        raise UnsupportedVerbError(str_mob(subject.mob), "add")


def ss_play(subject: State, query: Query) -> State:
    """Play the queried mob

    The query will be played in the context of the subject if valid.
    SS Objects will be deconstructed recursively.
    """
    if not query:
        query = subject.mob
    to_play = ss_open(subject, query).mob
    if subject.mob["type"] in ["playlist", "album", "show"] and mob_in_mob(
        subject.api, to_play, subject.mob
    ):
        _ss_play_in_context(subject.api, subject.mob, to_play)
    else:
        uri_list = list(
            iter_mob_uri(cast(SpotifyPKCE, subject.api.auth_manager), to_play)
        )
        subject.api.start_playback(uris=uri_list)
    return subject


def ss_all(subject: State, query: Query) -> State:
    """Open an empty, playlist-like SS Object

    Fills in a value for most keys in a Spotify PlaylistObject,
    excluding online-dependent ones. The new object will be named after
    the query.
    """
    if not query:
        # raise UnsupportedQueryError('"all" requires a query')
        raise UnsupportedQueryError("all", "")
    ss_object = Mob(
        frozendict(
            name=str_mob(query) if isinstance(query, Mapping) else query,
            owner=subject.api.me(),
            # Static:
            collaborative=False,
            description=None,
            images=(),
            public=None,
            snapshot_id=Ellipsis,  # This key could be helpful at some point
            objects=[],
            type="ss",
        )
    )
    return State(subject[0], ss_object, subject[2])


def ss_new(subject: State, query: Query) -> State:
    """Create a new playlist on Spotify for the current user

    The new playlist is private, and it is named after the query.
    """
    if not query:
        # raise UnsupportedQueryError('"new" requires a query')
        raise UnsupportedQueryError("new", "")
    name = str_mob(query) if isinstance(query, Mapping) else query
    playlist_id = cast(
        str,
        subject.api.user_playlist_create(
            cast(Mob, subject.api.me())["id"], name, False
        ),
    )
    return ss_open(subject, playlist_id)


def _ss_open_process_query(query: str) -> TypeSpecificSearch:
    if as_uri(query):
        return _ss_open_uri
    tags = {t: (t + ":" in query) for t in MOBNAMES}
    if tags["playlist"]:
        return _ss_open_playlist
    if tags["track"] and (tags["album"] or tags["artist"]):
        return _ss_open_track(variation=_ss_open_firstresult)
    if tags["track"]:
        return _ss_open_track(variation=_ss_open_userinput)
    if tags["album"] and tags["artist"]:
        return _ss_open_album(variation=_ss_open_firstresult)
    if tags["album"]:
        return _ss_open_album(variation=_ss_open_userinput)
    if tags["artist"]:
        return _ss_open_artist(variation=_ss_open_firstresult)
    return _ss_open_general


def _ss_open_uri(subject: State, query: str) -> Mob | None:
    api = subject[0]
    _, mobtype, mobid = as_uri(query).split(":")
    try:
        return MOB_GET_FUNCTIONS[mobtype](api, mobid)
    except KeyError:
        return None


def _ss_open_general(subject: State, query: str) -> Mob | None:
    api = subject[0]
    results = cast(dict, api.search(query, LIMIT, type=",".join(MOBNAMES)))
    results = {
        x: _ss_open_familiar(subject, results[x + "s"], x)
        if x != "playlist"
        else _ss_open_playlist_familiar(subject, results["playlists"])
        for x in MOBNAMES
    }
    for result_gens in roundrobin(
        *[
            zip(*[results[t] for t in mobtypes])
            for mobtypes in [MOBNAMES[-1:], MOBNAMES[:-1]]
        ]
    ):
        # Current result_gens: Iterable[Iterator[Iterator[Mob]]]
        # Desired result_gens: Iterable[Iterator[Mob]]
        # priority_results: Iterator[Mob]
        priority_results, pr_original = tee(roundrobin(*result_gens))
        if first_result := next(priority_results, None):
            if next(priority_results, None):
                get_full_object = MOB_GET_FUNCTIONS[first_result["type"]]
                return get_full_object(api, first_result["id"])
            if user_select := _ss_open_userinput(pr_original):
                get_full_object = MOB_GET_FUNCTIONS[user_select["type"]]
                return get_full_object(api, user_select["id"])
    return None


def _ss_open_playlist(subject: State, query: str) -> Playlist | None:
    api = subject[0]
    results = cast(dict, api.search(query, LIMIT, type="playlist"))[
        "playlists"
    ]
    results = _ss_open_playlist_familiar(subject, results)
    num_results, results_familiar = _ss_open_genlen(next(results))
    if num_results:
        result = api.playlist(next(results_familiar)["id"])
        return cast(Playlist | None, _ss_open_notifyuser(result))
    results_f1, results_f2 = tee(next(results))
    first_result = next(results_f1, None)
    if first_result and all(
        z[0] == z[1] for z in zip(first_result["name"], query)
    ):
        result = api.playlist(first_result)
        return cast(Playlist | None, _ss_open_notifyuser(result))
    if first_result:
        user_select = _ss_open_userinput(results_f2)
        if user_select:
            return cast(Playlist | None, api.playlist(user_select["id"]))
    num_results, results_familiar = _ss_open_genlen(next(results))
    if num_results == 1:
        result = api.playlist(next(results_familiar)["id"])
        return cast(Playlist | None, _ss_open_notifyuser(result))
    if num_results:
        user_select = _ss_open_userinput(next(results))
        if user_select:
            return cast(Playlist | None, api.playlist(user_select["id"]))
    return None


def _ss_open_playlist_familiar(
    subject: State, results: dict
) -> Iterator[Iterator[Playlist]]:
    api = subject[0]
    auth = cast(SpotifyPKCE, api.auth_manager)
    yield (
        cast(Playlist, p)
        for p in results['items']
        if p["id"] == subject[1].get("id", False)
    )
    usrid = cast(dict, api.me())["id"]
    yield (
        cast(Playlist, p)
        for p in results['items']
        if p["owner"]["id"] == usrid
    )
    yield (
        cast(Playlist, p)
        for p in results['items']
        if api.playlist_is_following(p["id"], [usrid])
    )
    yield cast(Iterator[Playlist], results_generator(auth, results))


def _ss_open_track(variation: MultipleChoiceFunction) -> TypeSpecificSearch:
    def get_track(subject: State, query: str) -> Track | None:
        api = subject[0]
        results = cast(dict, api.search(query, LIMIT, type="track"))["tracks"]
        results_tiered = _ss_open_familiar(subject, results, MOBNAMES[0])
        for unconfidence, tier in enumerate(results_tiered):
            num_results, results = _ss_open_genlen(tier)
            if num_results == 1 and unconfidence < 3:
                return cast(Track, next(results))
            if num_results:
                user_select = variation(
                    results,
                )
                # UNREACHED breakpoint()
                if user_select:
                    return cast(Track, user_select)
        # REACHED breakpoint()
        return None

    return get_track


def _ss_open_album(variation: MultipleChoiceFunction) -> TypeSpecificSearch:
    def get_album(subject: State, query: str) -> Album | None:
        api = subject[0]
        results = cast(dict, api.search(query, LIMIT, type="album"))["albums"]
        results = _ss_open_familiar(subject, results, MOBNAMES[0])
        for unconfidence, results in enumerate(results):
            num_results, results = _ss_open_genlen(results)
            if num_results == 1 and unconfidence < 3:
                return api.album(next(results)["id"])
            if num_results:
                user_select = variation(
                    results,
                )
                if user_select:
                    return cast(Album, api.album(user_select["id"]))
        return None

    return get_album


def _ss_open_artist(variation: MultipleChoiceFunction) -> TypeSpecificSearch:
    def get_artist(subject: State, query: str) -> Artist | None:
        api = subject[0]
        results = cast(dict, api.search(query, LIMIT, type="artist"))[
            "artists"
        ]
        results = _ss_open_familiar(subject, results, MOBNAMES[0])
        for unconfidence, results in enumerate(results):
            if unconfidence == 2:
                pass
            num_results, results = _ss_open_genlen(results)
            if num_results == 1 and unconfidence < 3:
                return next(results)
            if num_results:
                user_select = variation(
                    results,
                )
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


def _ss_open_familiar(
    subject: State, results: dict, mobname: str
) -> Iterator[Iterator[Mob]]:
    api = subject[0]
    auth = cast(SpotifyPKCE, api.auth_manager)
    yield (
        r
        for r in results['items']
        if mob_in_mob(api, r, subject[1])
    )
    artists_ungrouped = []
    indices_filtered = set()
    for index, result in enumerate(results['items']):
        artists_ungrouped += [(index, artist['id']) for artist in result.get('artists', [result])]
    indices_all, artist_ids = zip(*artists_ungrouped)
    for secondary_index, following in enumerate(api.current_user_following_artists(*artist_ids)):
        if following:
            indices_filtered.add(indices_all[secondary_index])
    yield (
        results['items'][index]
        for index in indices_filtered
    )
    liked_songs = liked_songs_cache_check(api)
    yield (
        r
        for r in results['items']
        if r["id"] in liked_songs[mobname]
    )
    yield (
        r
        for r in results['items']
        if any(
            a in liked_songs["artist"] for a in r.get("artists") or [r["id"]]
        )
    )
    yield results_generator(auth, results)


def _ss_open_firstresult(results: Iterator[Mob]) -> Mob:
    return cast(Mob, _ss_open_notifyuser(next(results)))


def _ss_open_userinput(results: Iterator[Mob]) -> Mob | None:
    suggestions_given = 0
    for suggestion in results:
        if IO_CONFIRM(f"Continue with {str_mob(suggestion)}?"):
            return suggestion
        if (suggestions_given := suggestions_given + 1) > NUMSUGGESTIONS:
            return None
    return None


def _ss_open_notifyuser(selection: Mob | None = None) -> Mob | None:
    if selection:
        IO_NOTIFY(f"Using {str_mob(selection)}")
        return selection
    IO_NOTIFY("Seach returned no results")
    return None


def _ss_add_to_playlist(api: Spotify, destination: Mob, target: Mob):
    if target["type"] == "artist":
        raise UnsupportedQueryError("add", str_mob(target))
    target_items = chunked(
        list(  # Prevents infinite loop on self-add
            iter_mob_uri(
                cast(SpotifyPKCE, api.auth_manager), target, keep_local=False
            )
        ),
        100,
    )
    for item_group in target_items:
        api.playlist_add_items(destination["id"], item_group)


def _ss_add_to_ss(ss_obj: Mob, new_mob: Mob) -> Mob:
    return type(ss_obj)(
        **{
            k: type(ss_obj[k])([new_mob, *ss_obj[k]])
            if k == "objects"
            else ss_obj[k]
            for k in ss_obj
        }
    )


def _ss_remove_from_playlist(api: Spotify, destination: Mob, target: Mob):
    if target["type"] == "artist":
        raise UnsupportedQueryError("remove", str_mob(target))
    # Cannot remove local items
    # See https://github.com/plamere/spotipy/issues/524
    target_items = chunked(
        set(
            iter_mob_uri(
                cast(SpotifyPKCE, api.auth_manager), target, keep_local=False
            )
        ),
        100,
    )
    for item_group in target_items:
        api.playlist_remove_all_occurrences_of_items(
            destination["id"], item_group
        )


def _ss_remove_from_ss(ss_obj: Mob, rm_mob: Mob) -> Mob:
    new_objects = [
        _ss_remove_from_ss(x, rm_mob) if x.get("objects") else x
        for x in ss_obj
        if not mob_eq(rm_mob, x)
    ]
    return type(ss_obj)(
        **{
            k: type(ss_obj[k])(new_objects) if k == "objects" else ss_obj[k]
            for k in ss_obj
        }
    )


def _ss_play_in_context(api: Spotify, context: Mob, to_play: Mob):
    context_gen = results_generator(
        cast(SpotifyPKCE, api.auth_manager), context["tracks"]
    )
    for obj in context_gen:
        if mob_in_mob(api, obj.get("track", obj), to_play):
            api.start_playback(
                context_uri=context["uri"], offset=obj.get("track", obj)
            )
            break


if __name__ == "__main__":
    from ._sh import login

    sp, usr, _ = login()
    sub = (sp, None)
    io_inject(lambda x: True)
    import doctest

    doctest.testmod()
