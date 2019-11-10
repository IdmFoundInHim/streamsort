# StreamSort [Project Briefing]

## Aim

Automatically catalog ranked projects into a database from playlists
to enable long-term preservation, detailed analytics, dynamic
organization and publishing.

## External Resources

- Spotify API
- MySQL

## Implementation Plan (Summary)

Use a Python installer to unpack the program's scripts, initiate a
database in the curent directory, and securely store API authentication.
Scripts include:
- One to be run at regular intervals to update the database with any
  new/changed rankings.
- A command line interface for analyzing the database