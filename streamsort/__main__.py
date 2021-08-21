""" CLI Initializer for StreamSort

Copyright (c) 2021 IdmFoundInHim, under MIT License

Usage: python3 -m streamsort
"""

import os
import sys
from importlib import import_module

import more_itertools

from ._constants import CACHE_DIR, EXTENSION_ATTRIBUTE
from ._sh import shell

if CACHE_DIR not in os.listdir():
    os.makedirs(CACHE_DIR)

extension_sentences = {}
for extension in more_itertools.lstrip(sys.argv, lambda a: "__main__.py" in a):
    extension_sentences |= import_module(extension).__dict__[
        EXTENSION_ATTRIBUTE
    ]

sys.exit(shell(extension_sentences))
