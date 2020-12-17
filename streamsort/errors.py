""" Special exceptions for StreamSort

Copyright (c) 2020 IdmFoundInHim
"""

class NoResultsError(ValueError):
    """ A Spotify search returned no results """

class UnexpectedResponseException(Exception):
    """ Spotify returned an object with an unfamiliar format """