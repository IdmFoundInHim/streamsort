import sqlite3 as sql
from string import ascii_letters, digits
from typing import Optional, Tuple
from datetime import datetime as ts, timedelta as td, date
from math import inf as infinity

ALPHANUM = ascii_letters + digits
Season = Tuple[int, int]


class SeasonIntersectionError(ValueError):
    """ An attempted action would have created seasons that would not be
    mutually exclusive. """
    pass


class SeasonMissingError(ValueError):
    """ An attempted action would have created seasons consecutive in
    date but not name. """
    pass


class SeasonGapError(ValueError):
    """ An attempted action would have created seasons consecutive in
    name but not date. """
    pass


class SeasonOrderError(ValueError):
    """ An attempted action would have created seasons whose names are
    not in the same order as their dates. """
    pass


class SeasonDuplicateError(SeasonOrderError):
    """An attempted action would have created seasons with the same
    name. """
    pass


class SeasonNameError(ValueError):
    """ An attempted action would have created a season with an invalid
    name. """
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
        prev: date = date(end.year, 1, 1)
        nexts = None
        for s in year_seasons:
            if s[1] <= end and not s[2] < end:
                raise SeasonIntersectionError
            if s[1] > end:
                nexts = s
                break
            prev = s
        prev_name = parse_name(prev[0])
        nexts_name = parse_name(nexts[0])
        if start is None:
            assert prev_name[0] == end.year
            start, name = prev[1] + td(days=1), (end.year, prev[2] + 1)
            if nexts is not None and nexts_name <= name:
                set_refactor_gap(end.year)
        else:
            if start >= end or start.year != end.year:
                raise ValueError
            if prev[2] >= start:
                raise SeasonIntersectionError
            if True:
                if prev[2] + td(days=1) == start:
                    name_req = (end.year, prev_name[1] + 1)
                    if (nexts[1] - td(days=1) == end
                       and name_req != (end.year,
                                        nexts_name[1] - 1)):
                        raise SeasonMissingError
                    if nexts_name == name_req:
                        set_refactor_gap(end.year)
                elif nexts[1] - td(days=1) == end:
                    name_req = (end.year, nexts_name[1] - 1)
                    if prev_name == name_req:
                        set_refactor_gap(end.year)
                elif name is not None:
                    name_req = None
                    if name < prev_name or name > nexts_name:
                        raise SeasonOrderError
                    if name == prev_name or name == nexts_name:
                        raise SeasonDuplicateError
                    if name[1] == prev_name[1] + 1:
                        raise SeasonGapError
                else:
                    name_req = None
                    name = (end.year, prev_name[1] + 2)
                if name is None:
                    name = name_req
                # name is now filled, one way or another
                elif name_req is None:
                    if name[1] >= nexts_name[1] - 1:
                        raise SeasonGapError
                if name != name_req:
                    if name < prev_name or name > nexts_name:
                        raise SeasonOrderError
                    if name == prev_name or name == nexts_name:
                        raise SeasonDuplicateError
                    else:
                        raise SeasonMissingError

    write = library.cursor()
