import sqlite3 as sql
from datetime import date
from datetime import datetime as ts
from datetime import timedelta as td
from math import inf as infinity
from string import ascii_letters, digits
from typing import Any, Callable, Optional, Tuple

ALPHANUM = ascii_letters + digits
Season = Tuple[int, int]
PUNCTUATION = ",;.!'\"`+*^-/\\%@:?&#()[]{}<>=~$"
PRINTABLE = digits + ascii_letters + PUNCTUATION


class DBSeasonGapError(ValueError):
    """ The database contains seasons consecutive in name but not
    date. """
    pass


class SeasonGapError(ValueError):
    """ An attempted action would have created seasons consecutive in
    name but not date. """
    pass


class SeasonIntersectionError(ValueError):
    """ An attempted action would have created seasons that would not be
    mutually exclusive. """
    pass


class SeasonMissingError(ValueError):
    """ An attempted action would have created seasons consecutive in
    date but not name. """
    pass


class SeasonOrderError(ValueError):
    """ An attempted action would have created seasons whose names are
    not in the same order as their dates. *Includes Duplicate Errors*
    """
    pass


class SeasonDuplicateError(SeasonOrderError):
    """An attempted action would have created seasons with the same
    name. *Is a subtype of Order Error*"""
    pass


def increment(obj):
    if isinstance(obj, str):
        return PRINTABLE[PRINTABLE.index(obj[-1]) + 1]
    if isinstance(obj, complex):
        realadd = obj.real / (obj.real + obj.imag)
        return obj.real + realadd + obj.imag + (1 - realadd) * 1j
    if isinstance(obj, (list, tuple, bytes, bytearray)):
        return obj[:-1] + type(obj)([increment(obj[-1])])
    if isinstance(obj, range):
        return range(obj.start + 1, obj.stop + 1)
    if isinstance(obj, (set, frozenset)):
        return {increment(x) for x in obj}
    if isinstance(obj, dict):
        return {k:increment(v) for k, v in obj.items()}
    if obj is None:
        return
    return obj + 1



def initialize_library(location: str, dbname: str):
    dblink = sql.connect(location)
    dbc = dblink.cursor()
    dbc.executescript("""
        CREATE DATABASE ?;
        CREATE TABLE index (
            internal_id TEXT PRIMARY KEY,
            external_id TEXT,
            title TEXT,
            artist TEXT,
            release_date DATE
        );
        CREATE TABLE guide (
            name TEXT PRIMARY KEY,
            start DATE,
            end date,
            ext_name TEXT,
            ext_id TEXT
        );
    """, (dbname))
    dblink.commit()
    dbc.close()
    return dblink

# CREATE TABLE S2020_1 ()


def is_spid(string: str):
    if len(string) != 22:
        return False
    for char in string:
        if char not in ALPHANUM:
            return False
    return True


def parse_name(table_name: str):
    if table_name[0] != 'S':
        raise ValueError
    return (int(table_name[1:5]), int(table_name[6:]))


def add_season(library: sql.Connection, end: Optional[date] = None,
               start: Optional[date] = None, name: Optional[Season] = None, /):
    """ Principles:
    1. Database is right more often than User
    2. Dates are right more often than Names
    """
    if library is not sql.Connection:
        raise TypeError
    if end is None:
        return add_season(library, *add_season_default_end(library))
    elif start is None:
        return add_season(library, end, add_season_default_start(end))
    elif name is None:
        name = add_season_default_name(library, end, start)
    add_season_validate()


def add_season_default_end(library: sql.Connection) -> Tuple[date, date,
                                                             Tuple[int, int]]:
    prevname, prevdate = library.cursor().execute("""
        SELECT name, end FROM guide
        LIMIT 1
        ORDER BY name DESC;
    """).fetchone()
    return (date.today(), prevdate + td(days=1),
    ((prevseason := parse_name(prevname))[0], prevseason[1] + 1))


def add_season_default_start(library: sql.Connection, end: date) -> date:
    year_seasons = library.cursor().execute("""
        SELECT start, end FROM guide
        WHERE name LIKE ?
        WHERE start <= ?
        ORDER BY name DESC;
    """, (f'S{end.year}%', end))
    prev = date(end.year - 1, 12, 31)
    for s in year_seasons:
        if s[0] <= end and not s[1] < end:
            raise SeasonIntersectionError
        if s[1] > end:
            return prev[2] + td(days=1)
        prev = s
    return date(end.year, 12, 31)


def add_season_default_name(library: sql.Connection, end: date, start: date):
    dateread = library.cursor()
    prevs = dateread.execute("""
        SELECT name, start, end FROM guide
        WHERE name LIKE ?
        WHERE end < ?
        ORDER BY name DESC
        LIMIT 1;
    """, (f'{end.year}%', start)).fetchone()
    nexts = dateread.execute("""
        SELECT name, start, end FROM guide
        WHERE name LIKE ?
        WHERE start > ?
        ORDER BY name ASC
        LIMIT 1
    """, (f'{end.year}%', prevs[2])).fetchone()
    name_nums = [parse_name(prevs[0])[1], parse_name(nexts[0])[1]]
    if prevs[2] + td(days=1) == start:
        return (end.year, name_nums[0] + 1)
    elif nexts[1] - td(days=1) == end:
        return (end.year, name_nums[1] - 1)
    else:
        return (end.year, name_nums[0] + 2)



def add_season_validate(library: sql.Connection, end: date, start: date,
                        name: Season):
    """ Rules:
    1. Check for blatantly invalid dates
    1. Check for SeasonIntersection
    1. Check for SeasonGap/Missing/Order
    """
    if not all(isinstance(end, date) and isinstance(start, date) 
               and isinstance(name, Tuple)):
        raise TypeError
    if end <= start:
        raise ValueError
    dbread = library.cursor()
    if not start.year == end.year == name[0]:
        raise ValueError

    if dbread.execute("SELECT name WHERE name LIKE ?",
                      (f'S{name[0]}-{name[1]}')).fetchone():
        raise SeasonDuplicateError

    year_seasons = dbread.execute("""
        SELECT name, start, end
        WHERE name LIKE ?
        SORT BY name ASC
    """, (f'S{name[0]}%')).fetchall()
    for s in year_seasons:
        if s[1] < end and s[2] > start:
            raise SeasonIntersectionError
        if s[1] > end:
            nexts = s
            break
        prevs = s

    approved_nums = range(parse_name(nexts[0])[1] + 1, parse_name(prevs[0])[1])
    if name[1] not in approved_nums:
        raise SeasonOrderError

    adjacent_start = prevs[2] + 1 == start
    adjacent_end = nexts[1] - 1 == end
    if len(approved_nums) < 1:
        raise DBSeasonGapError
    if adjacent_start and adjacent_end and len(approved_nums) != 1:
        raise SeasonMissingError
    if len(approved_nums) < 3 - adjacent_start - adjacent_end:
        raise SeasonGapError


def set_refactor_gap(library, year,
                     rerun: Callable = None, params: list = None):
    raise NotImplementedError
    # Work on this later
    return rerun(*params)
