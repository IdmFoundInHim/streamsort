import sqlite3 as sql
from string import ascii_letters, digits
from typing import Optional, Tuple
from datetime import datetime as ts, timedelta as td, date

ALPHANUM = ascii_letters + digits
Season = Tuple[int, int]


class SeasonIntersectionError(ValueError):
    """ An attempted action would have created seasons that would not be
    mutually exclusive. """
    pass




def initialize_library(location: str, dbname: str):
    dblink = sql.connect(location)
    with dblink.cursor() as dbc:
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
    elif start is None:
        # end determines start.year, name[0]
        year_seasons = dateread.execute("""
            SELECT name, start, end FROM guide
            WHERE name LIKE ?
            ORDER BY name DESC;
        """, f'S{end.year}%')
        prev: date = date(end.year, 1, 1)
        for season in year_seasons:
            if season[1] <= end and not season[2] < end:
                raise SeasonIntersectionError
            if season[1] > end:
                break
            prev = season
        assert parse_name(prev[0])[0] == end.year
        start, name = prev[1] + td(days=1), (end.year, prev[2] + 1)
    elif name is None:
        if start >= end:
            raise ValueError
        # Continue


        

