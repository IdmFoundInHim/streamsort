# StreamSort ©2019 IdmFoundInHim
# Command Line Interface
from itertools import zip_longest

state = {'_exit_status': 0, "_var": {}}
SPACE = ' '
SQUOT = '\''
DQUOT = '"'
ESCAP = '\\'
NULL = ''


def prompt(state):
    state_print(state)
    cmd = parse_input(input('> '))


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


# grouper from itertools recipes,
# https://docs.python.org/3.6/library/itertools.html#itertools-recipes
def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


def flatten(lst):
    return [item for sublist in lst for item in sublist]


def remove_escapes(string):
    return string.replace('\\', '')


def escaper(mode):
    return lambda char, index: (None, mode)


def watchdog(flag_char, watch_chars):
    def watch_x(char, index):
        if char == flag_char:
            return (None, flagger(index))
        if char == ESCAP:
            return (None, escaper(watch_x))
        if char in watch_chars:
            return (None, watchdog(char, NULL))
        return (None, watch_x)
    return watch_x


def flagger(start, end=None):
    if end is None:
        end = start + 1

    def flag(char, index):
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
    for start, stop in grouper([0] + flatten(flags) + [len(rawin)], 2):
        yield remove_escapes(rawin[start:stop])

while not state['_exit_status']:
    state = prompt(state)
