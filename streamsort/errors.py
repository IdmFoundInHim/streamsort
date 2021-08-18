""" Special exceptions for StreamSort

Copyright (c) 2021 IdmFoundInHim, under MIT License
"""
__all__ = ['NoResultsError', 'UnexpectedResponseException',
    'UnsupportedQueryError', 'UnsupportedVerbError']

class NoResultsError(ValueError):
    """ A Spotify search returned no results """

class UnsupportedVerbError(ValueError):
    """ The Subject did not allow the attempted Sentence """

    def __init__(self, subject: str, verb: str):
        super().__init__()
        self.args = (f'{subject} does not allow you to use "{verb}"',
                     *self.args)

class UnsupportedQueryError(ValueError):
    """ A Sentence was attempted with a disallowed (but understood) Query """

    def __init__(self, verb: str, query: str):
        super().__init__()
        self.args = (f'"{verb}" is unable to process {query}',
                     *self.args)

class UnexpectedResponseException(Exception):
    """ Spotify returned an object with an unfamiliar format """
