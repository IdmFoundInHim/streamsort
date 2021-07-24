""" CLI Initializer for StreamSort

Copyright (c) 2021 IdmFoundInHim, under MIT License

Usage: python3 -m streamsort
"""
import os
import sys

from .constants import CACHE_DIR

from .sh import shell

if CACHE_DIR not in os.listdir():
    os.makedirs(CACHE_DIR)

sys.exit(shell())
