""" CLI for StreamSort

Copyright (c) 2021 IdmFoundInHim, under MIT License

Basic rules:
    * Spaces seperate tokens as each line is interpreted left-to-right
    * Symbols have no special meaning to avoid interfering with music
      object (track, album, playlist, artist) names
    * The main state variable is the active subject/location which is
      a user or a music object ("mob")
    * Variables are implemented as subshells
        A subshell is a copy of the current state. Commands can be run
        one at a time to utilize and modify the subshell from the main
        shell, and the subshell can be loaded to the main state. More
        details are below.
    * All tokens can be processed without subsequent tokens
    * Subshell names are a secondary state variable that extend the
      reserved tokens
    * All functions take one parameter

All reserved keywords:
    Functions: get, open, all, add, play, new, remove
        Builtins: shuffle, projects
    Control: in, after, track, nom

Control Syntax:
    Basic `> {function} Parameter is Remainder of Line`
    Subshell Initiation `> subshell-name {Line-Optional}`
        (Yes, `subsh subsub trisub` is valid)
    Subshell Extension `> in subshell-name {Line}`
    Subshell Loading `> subshell-name`
    Pipeline `> {function} after {Line}`
        This will pass the output (resulting subject) of Line to
        function as the parameter.
    Subject Reference `> {function-Optional} track {Number}`
        Gets the Number-th track of the open mob, passing it to function
        or loading it. Rather than Number, the full Track name can also
        be specified, case-insensitive
    Escape `{function} nom Parameter Starting With Reserved Token`
        Drops interpreter into free mode from branch mode
        (Yes, `open nom nom` is valid)

Subshells:
    When a non-reserved token appears anywhere a reserved token is
    required (e.g. opening a line), a new subshell is created. The
    subshell inherits the active state, and the remainder of the line is
    run as a new line. Any state changes will affect the subshell state
    and not the main state. The subshell is added to the main state as
    a token-state pair of the first token and the subshell state,
    respectively.

    Then, the subshell can be invoked one of two ways. Typically, the in
    keyword will be used (`in subsh {function}...`), to run a function
    extending the subshell. Any references in the parameter, like
    `track 4` or `othersubshell`, will use the main state, but the
    function will use and/or change the subshell state. Additionally,
    a subshell may be used as the first token of a line to load the
    subshell state into the main state.

    The idiom for loading a subshell while saving the main state is as
    follows, with an arbitrary name for backtomain:
    ```streamx
    > in subsh backtomain
    > subsh
    ```
    Use `> backtomain` to restore the original state.

Implementation:
    * The interpreter reads in one of three modes:
      1. reserved: Expecting a keyword
      2. free: Expecting words that are part of a parameter
      3. branch: Watching for keywords, but otherwise acts like free
    * In reserved mode, non-reserved tokens are new subshell names
"""
__all__ = ["shell", "process_line", "login", "logout"]

import os
import itertools
from collections.abc import Callable, Iterator, Mapping
from typing import cast

from frozendict import frozendict
import requests.exceptions
from spotipy import Spotify, SpotifyException, SpotifyPKCE

from ._constants import CACHE_PATH, CLIENT_ID, REDIRECT_URI, SCOPE
from .errors import NoResultsError
from .sentences import ss_add, ss_all, ss_new, ss_open, ss_play, ss_remove
from .types import Mob, Query, Sentence, State
from .utilities import iter_mob_track, results_generator, str_mob

SAFE = 0
IDLE = 1
WORK = 2


def login() -> State:
    """Returns an authorized Spotify object and user details"""
    spotify = Spotify(
        auth_manager=SpotifyPKCE(
            client_id=CLIENT_ID,
            redirect_uri=REDIRECT_URI,
            cache_path=CACHE_PATH,
            scope=SCOPE,
        )
    )
    user = cast(Mob, spotify.me())
    return State(spotify, user)


def logout() -> int:
    """Removes cache, returning a truthy value only if removal fails"""
    try:
        os.remove(CACHE_PATH)
        return 0
    except OSError:
        return 1


def shell(extensions: dict[str, Sentence]) -> int:
    sentences: frozendict[str, Sentence] = frozendict(
        {
            "open": ss_open,
            "add": ss_add,
            "remove": ss_remove,
            "play": ss_play,
            "all": ss_all,
            "new": ss_new,
            "get": ss_open,
            **extensions,
        }
    )
    status = IDLE
    state = login()
    while (line := input(str_mob(state.mob) + " > ")) != "exit":
        status = WORK
        if line[:6] == "logout":
            if logout():
                print("Logout failed")
            else:
                del state
                input("Press Enter to Login")
                state = login()
        else:
            try:
                sentence, query = process_line(
                    state, iter(line.split()), sentences
                )
                state = sentence(state, query)
            except NoResultsError:
                print("    No Results")
            except SpotifyException:
                print("    ERROR: The Spotify operation failed")
            except ValueError as err:
                print(f"    ERROR: {err.args[0]}")
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.ReadTimeout,
            ):
                print("    ERROR: Connection was lost. Reconnecting...")
                state = State(login().api, state[1], state[2])
        status = IDLE
    status = SAFE
    return status


Processor = Callable[
    [State, Iterator[str], Mapping[str, Sentence]], tuple[Sentence, Query]
]
QueryProcess = Callable[[State, Iterator[str], Mapping[str, Sentence]], Query]


def process_line(
    state: State, tokens: Iterator[str], sentences: Mapping[str, Sentence]
) -> tuple[Sentence, Query]:
    reserved_control: dict[str | None, Processor] = {
        "in": _process_line_in,
        "after": process_line,
        "track": _process_line_track_load,
        "nom": lambda a, b, c: (_identity_state, Mob({})),
        None: lambda a, b, c: (_identity_state, Mob({})),
    }
    branch_control: dict[str | None, QueryProcess | str] = {
        "in": "Parameter may not start with 'in'. Perhaps use 'nom in'",
        "after": _process_line_after,
        "track": _process_line_track,
        "nom": _process_line_nom,
    }

    token = next(tokens, None)
    if processor := reserved_control.get(token):
        return processor(state, tokens, sentences)
    if sentence := sentences.get(cast(str, token)):
        tokens_t, branch_tokens = itertools.tee(tokens)
        branch_token = next(branch_tokens, None)
        if control := cast(QueryProcess, branch_control.get(branch_token)):
            try:
                return (sentence, control(state, tokens, sentences))
            except TypeError as err:
                raise ValueError(control) from err
        return (sentence, " ".join(tokens_t))
    if substate := state.subshells.get(cast(str, token)):
        subsh_name, token = token, next(tokens, None)
        if token:
            raise ValueError(
                "Subshell loading does not take a parameter. "
                f"Perhaps use 'in {subsh_name}..."
            )
        return ((lambda a, b: cast(State, substate)), "")
    return _process_line_make_subsh(state, tokens, sentences, cast(str, token))


def _process_line_make_subsh(
    state: State,
    tokens: Iterator[str],
    sentences: Mapping[str, Sentence],
    new_subshell: str,
) -> tuple[Sentence, Query]:
    sentence, query = process_line(state, tokens, sentences)
    return (_set_subshell(new_subshell, sentence(state, query)), Mob({}))


def _process_line_in(
    state: State, tokens: Iterator[str], sentences: Mapping[str, Sentence]
) -> tuple[Sentence, Query]:
    try:
        subsh = next(tokens)
    except StopIteration as err:
        raise ValueError("Missing subshell name after 'in'") from err
    try:
        sentence, query = process_line(state, tokens, sentences)
        return (
            _set_subshell(subsh, sentence(state[2][subsh], query)),
            Mob({}),
        )
    except KeyError as err:
        raise ValueError("Invalid subshell name after 'in'") from err


def _process_line_track(
    state: State, tokens: Iterator[str], sentences: Mapping[str, Sentence]
) -> Mob:
    del sentences
    track_num = next(tokens)
    try:
        track_num = int(track_num)
        track = state.mob["tracks"]["items"][track_num - 1]
        return cast(Mob, state.api.track(track.get("track", track)["id"]))
    except KeyError as err:
        raise ValueError(f"'{str(state)}' does not contain tracks") from err
    except IndexError:
        all_tracks = results_generator(
            cast(SpotifyPKCE, state.api.auth_manager), state.mob["tracks"]
        )
        targeted_track_num = 1
        while targeted_track_num != track_num and next(all_tracks, False):
            targeted_track_num += 1
        if targeted_track := next(all_tracks, None):
            targeted_track = targeted_track.get("track", targeted_track)["id"]
            return cast(Mob, state.api.track(targeted_track))
    except ValueError:
        pass
    track_nom = " ".join(tokens)
    if track_num != "nom":
        track_nom = f"{track_num} {track_nom}".lower()
    track_obj = next(
        (
            t
            for t in iter_mob_track(
                cast(SpotifyPKCE, state.api.auth_manager), state.mob
            )
            if track_nom == t["name"].lower()
        ),
        None,
    )
    if not track_obj:
        raise ValueError(f"Track {track_nom} was not found")
    return cast(Mob, state.api.track(track_obj["id"]))


def _process_line_track_load(
    state: State, tokens: Iterator[str], sentences: Mapping[str, Sentence]
) -> tuple[Sentence, Query]:
    mob = _process_line_track(state, tokens, sentences)
    new_state = State(state[0], mob, state[2])
    return ((lambda a, b: new_state), "")


def _process_line_after(
    state: State, tokens: Iterator[str], sentences: Mapping[str, Sentence]
) -> Mob:
    subject, query = process_line(state, tokens, sentences)
    return subject(state, query).mob


def _process_line_nom(
    state: State, tokens: Iterator[str], sentences: Mapping[str, Sentence]
) -> str:
    del state, sentences
    return " ".join(tokens)


def _set_subshell(subsh_name: str, subsh_state: State) -> Sentence:
    def set_subshell(subject: State, query: Query) -> State:
        del query
        old_subshells = {
            k: subject.subshells[k]
            for k in subject.subshells
            if k != subsh_name
        }
        subshells = frozendict(old_subshells | {subsh_name: subsh_state})
        return State(subject[0], subject[1], subshells)

    return set_subshell


def _identity_state(state: State, query: Query) -> State:
    del query
    return state
