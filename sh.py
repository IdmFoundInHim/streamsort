# StreamSort ©2019 IdmFoundInHim
# Command Line Interface
from itertools import chain, zip_longest
from typing import Callable, Optional, Tuple, Union

state = {'_exit_status': 0, "_var": {}}
SPACE = ' '
SQUOT = '\''
DQUOT = '"'
ESCAP = '\\'
NULL = ''
SPEC = SQUOT + DQUOT + ESCAP + SPACE


def prompt(state):
    print_state(state)
    cmds = parse_input(input('> '))


def print_state(state):
    for key, val in state.items():
        if type(val) is str:
            if key[0] != '_':
                print(val, end=SPACE)
        elif type(val) is dict:
            try:
                print(val['__str__'], end=SPACE)
            except KeyError:
                pass
        elif type(val) in (list, tuple):
            if val != []:
                print(val[0], end=SPACE)


# `grouper` and `flatten` from itertools recipes,
# https://docs.python.org/3.8/library/itertools.html#itertools-recipes
def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


def flatten(list_of_lists):
    "Flatten one level of nesting"
    return chain.from_iterable(list_of_lists)


def remove_escapes(string):
    return string.replace(ESCAP, NULL)


def escaper(mode):
    """ Builds escape mode, which does nothing
    except return the previous mode with no flag """
    return lambda char, index: (None, mode)


def watchdog(flag_char, watch_chars):
    """ Builds watch mode to initiate flag at flag_char,
    initiate escape at \\, initiate a new watch at
    any of watch_char, or return itself without a
    flag """
    def watch_x(char, index):
        """ See `watchdog.__doc__` """
        if char == flag_char:
            return (None, flagger(index))
        if char == ESCAP:
            return (None, escaper(watch_x))
        if char in watch_chars:
            return (None, watchdog(char, NULL))
        return (None, watch_x)
    return watch_x


def flagger(start: int,
            end: Optional[int] = None) -> Tuple[Optional[List[int, int]],
                                                Callable]:
    """ Initiates/continues flag mode

    In flag mode, a non-space character will end a flag (including it
    as `OUT[0]`). Special characters expand the flag before ending it.
    (`OUT[1]` will be a non-flag mode.)

    A space expands the flag. `OUT[0] is None`, and `OUT[1]` will be a
    new flagger -- expanding the existing flag.
    """
    if end is None:
        end = start + 1

    def flag(char, index):
        """ See `flagger.__doc__` """
        if char == SPACE:
            return (None, flagger(start, end + 1))
        if char in SQUOT + DQUOT + ESCAP:
            return ([start, end + 1], default(char, index)[1])
        else:
            return ([start, end], default)
    return flag


default = watchdog(SPACE, SQUOT + DQUOT)


def parse_input(rawin):
    mode = default
    flags = []
    for i in range(len(rawin)):
        flag, mode = mode(rawin[i], i)
        if flag:
            flags.append(flag)
    if (flag := mode('', len(rawin))[0]):
        flags.append(flag)
    start = 0
    for i in range(len(rawin)):
        if rawin[i] not in SPEC:
            start = i
            break
    for start, stop in grouper([start] + flatten(flags) + [len(rawin)], 2):
        yield remove_escapes(rawin[start:stop])


while not state['_exit_status']:
    state = prompt(state)
