""" Copyright (c) 2020 IdmFoundInHim, under MIT license

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
    Pipeline `> {function-Optional} after {Line}`
        This will pass the output (resulting subject) of Line to
        function as the parameter. Without function, after is
        superfluous.
    Subject Reference `> {function-Optional} track {Number}`
        Gets the Number-th track of the open mob, passing it to function
        or returning it
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

import os
from typing import Callable, Iterable, Iterator, Optional, Union

from spotipy import Spotify, SpotifyPKCE

from .constants import CACHE_PATH, CLIENT_ID, REDIRECT_URI, SCOPE
from .errors import NoResultsError
from .musictypes import Mob, State
from .sentences import ss_open

SAFE = 0
IDLE = 1
WORK = 2


def shell() -> int:
    status = IDLE
    state = State(*login())
    while (line := input(str(state) + ' > ')) != 'exit':
        status = WORK
        if line[:6] == 'logout':
            if logout():
                print('Logout failed')
            else:
                del state
                input('Press Enter to Login')
                state = State(*login())
        else:
            try:
                sentence, query = process_line(state, iter(line.split()))
                state = sentence(state, query)
            except NoResultsError:
                print('    No Results')
            except ValueError as err:
                print(f'    ERROR: {err.args[0]}')
        status = IDLE
    status = SAFE
    return status


sentences = {'open': ss_open}
Query = Union[str, Mob]
Sentence = Callable[[State, Query], State]
Processor = Callable[[State, Iterator[str]], tuple[Sentence, Query]]
QueryProcess = Callable[[State, Iterator[str]], Query]

def process_line(state: State,
                 tokens: Iterator[str]) -> tuple[Sentence, Query]:
    reserved_control: dict[Optional[str], Optional[Processor]] = {
        'in': _process_line_in,
        'after': process_line,
        'track': None,
        'nom': None,
        None: lambda a, b: (_identity_state, Mob({}))
    }
    branch_control: dict[Optional[str], Union[QueryProcess, str]] = {
        'in': "Parameter may not start with 'in'. Perhaps use 'nom in'",
        'after': _process_line_after,
        'track': _process_line_track,
        'nom': _process_line_nom,
        None: "Missing Parameter"
    }

    token = next(tokens, None)
    if control := reserved_control.get(token):
        try:
            return control(state, tokens)
        except TypeError as err:
            raise ValueError(f"Lines starting with '{token}' "
                              "do nothing") from err
    if sentence := sentences.get(token):
        token = next(tokens, None)
        if control := branch_control.get(token):
            try:
                return (sentence, control(state, tokens))
            except TypeError as err:
                raise ValueError(control) from err
        return (sentence, token + ' '.join(tokens))
    if substate := state.subshells.get(token):
        subsh_name, token = token, next(tokens, None)
        if token:
            raise ValueError("Subshell loading does not take a parameter. "
                             f"Perhaps use 'in {subsh_name}...")
        return ((lambda a, b: substate), '')
    return _process_line_init_subsh(state, tokens, token)


def _process_line_init_subsh(state: State,
                             tokens: Iterator[str],
                             new_subshell: str) -> tuple[Sentence, Query]:
    subject, query = process_line(state, tokens)
    state.subshells[new_subshell] = subject(state, query)
    return (_identity_state, Mob({}))


def _process_line_in(state: State,
                     tokens: Iterable[str]) -> tuple[Sentence, Query]:
    try:
        subsh = next(tokens)
    except StopIteration as err:
        raise ValueError("Missing subshell name after 'in'") from err
    try:
        subject, query = process_line(state, tokens)
        state.subshells[subsh] = subject(state[2][subsh], query)
        return (_identity_state, Mob({}))
    except KeyError as err:
        raise ValueError("Invalid subshell name after 'in'") from err


def _process_line_track(state: State, tokens: Iterator[str]) -> Mob:
    track_num = next(tokens)
    try:
        return state.mob['tracks']['items'][int(track_num) - 1]
    except (KeyError, ValueError):
        track_nom = ' '.join(tokens)
        if track_num != 'nom':
            track_nom = f'{track_num} {track_nom}'
        query = next((t for t in state.mob['tracks']['items']
                        if track_nom == t['name']), None)
    if not query:
        raise ValueError(f"Track {track_nom} was not found")
    return query


def _process_line_after(state: State, tokens: Iterator[str]) -> Mob:
    subject, query = process_line(state, tokens)
    return subject(state, query).mob


def _process_line_nom(state: State, tokens: Iterator[str]) -> str:
    del state
    return ' '.join(tokens)


def _identity_state(state: State, query: Query) -> State:
    del query
    return state


def login() -> State:
    """ Returns an authorized Spotify object and user details """
    spotify = Spotify(auth_manager=SpotifyPKCE(client_id=CLIENT_ID,
                                               redirect_uri=REDIRECT_URI,
                                               cache_path=CACHE_PATH,
                                               scope=SCOPE))
    user = spotify.me()
    return State(spotify, user)


def logout() -> int:
    """ Removes cache, returning a truthy value only if removal fails
    """
    try:
        os.remove(CACHE_PATH)
        return 0
    except OSError:
        return 1
