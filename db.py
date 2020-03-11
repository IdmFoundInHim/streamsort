import sqlite3 as sql
from datetime import date
from datetime import datetime as ts
from datetime import timedelta as td
from math import inf as infinity
from string import ascii_letters, digits
from typing import Callable, Optional, Tuple

ALPHANUM = ascii_letters + digits
Season = Tuple[int, int]


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
    dateread = library.cursor()
    if end is None:
        # All auto
        prevname, prevdate = dateread.execute("""
            SELECT name, end FROM guide
            LIMIT 1
            ORDER BY name DESC;
        """).fetchone()
        start, end = prevdate + td(days=1), date.today()
        name = (prevseason := parse_name(prevname))[0], prevseason[1] + 1
    else:
        # end determines start.year, name[0]
        year_seasons = dateread.execute("""
            SELECT name, start, end FROM guide
            WHERE name LIKE ?
            ORDER BY name DESC;
        """, f'S{end.year}%')
        prev = (f"{end.year}-0", date(end.year - 1, 12, 31),
                date(end.year - 1, 12, 31))
        nexts = None
        for s in year_seasons:
            if s[1] <= end and not s[2] < end:
                raise SeasonIntersectionError
            if s[1] > end:
                nexts = s
                break
            prev = s
        prev_name = parse_name(prev[0])
        if nexts is not None:
            nexts_name = parse_name(nexts[0])
        else:
            nexts_name = (end.year, 53)
        if start is None:
            assert prev_name[0] == end.year
            start, name = prev[2] + td(days=1), (end.year, prev_name[1] + 1)
            if nexts is not None and nexts_name <= name:
                return set_refactor_gap(library, end.year, rerun=add_season,
                                        params=[library, end, start, name])
        else:
            if start >= end or start.year != end.year:
                raise ValueError
            if prev[2] >= start:
                raise SeasonIntersectionError

            if prev[2] + td(days=1) == start:
                name_req = (end.year, prev_name[1] + 1)
                if nexts_name == name_req:
                    return set_refactor_gap(library, end.year,
                                            rerun=add_season,
                                            params=[library, end, start, name])
                if (nexts[1] - td(days=1) == end
                   and name_req != (end.year,
                                    nexts_name[1] - 1)):
                    raise SeasonMissingError
            elif nexts[1] - td(days=1) == end:
                name_req = (end.year, nexts_name[1] - 1)
                if prev_name == name_req:
                    return set_refactor_gap(library, end.year,
                                            rerun=add_season,
                                            params=[library, end, start, name])
                if prev_name[1] - 1 == name_req[1]:
                    raise SeasonGapError
            elif name is not None:
                if name < prev_name or name > nexts_name:
                    raise SeasonOrderError
                if name == prev_name or name == nexts_name:
                    raise SeasonDuplicateError
                if name[1] == prev_name[1] + 1 or name[1] == nexts_name[1] - 1:
                    raise SeasonGapError
                name_req = None
            else:
                name = (end.year, prev_name[1] + 2)
                if name[1] == nexts_name[1] - 1:
                    raise SeasonGapError
                if name[1] == nexts_name[1]:
                    raise SeasonDuplicateError
                name_req = None

            if name is None:
                # i.e. if name is automatic and season is contiguous
                name = name_req
            if name_req is not None and name != name_req:
                # i.e. if name is manual and season is contiguous
                if name < prev_name or name > nexts_name:
                    raise SeasonOrderError
                if name == prev_name or name == nexts_name:
                    raise SeasonDuplicateError
                else:
                    raise SeasonMissingError

    write = library.cursor()


def set_refactor_gap(library, year,
                     rerun: Callable = None, params: list = None):
    raise NotImplementedError
    # Work on this later
    return rerun(*params)
