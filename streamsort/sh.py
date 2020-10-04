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
        Gets the Number-th track of the open mob, passing it to unction
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

from spotipy import Spotify, SpotifyPKCE

from .constants import CACHE_PATH, CLIENT_ID, REDIRECT_URI, SCOPE


def login() -> tuple[Spotify, dict]:
    """ Returns an authorized Spotify object and user details """
    spotify = Spotify(auth_manager=SpotifyPKCE(client_id=CLIENT_ID,
                                               redirect_uri=REDIRECT_URI,
                                               cache_path=CACHE_PATH,
                                               scope=SCOPE))
    user = spotify.me()
    return spotify, user


def logout() -> int:
    """ Removes cache, returning a truthy value only if removal fails
    """
    try:
        os.remove(CACHE_PATH)
        return 0
    except OSError:
        return 1
