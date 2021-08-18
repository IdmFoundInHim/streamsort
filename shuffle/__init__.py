""" StreamSort Shuffle Extension

Copyright (c) 2021 IdmFoundInHim, under MIT License

Included with StreamSort as an example  of how to extend StreamSort.
Notice that a `_sentences_` attribute is included in the top-level
package. This is required for the StreamSort shell to properly import
the extension.
"""
# pyright: reportUnsupportedDunderAll=false
from .sentences import __all__ as sentences__all__

__all__ = ['_sentences_'] + sentences__all__

from .sentences import *

_sentences_ = {'shuffle': shuf_shuffle}