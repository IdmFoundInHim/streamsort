""" Default I/O functions for StreamSort

Copyright (c) 2021 IdmFoundInHim, under MIT License
"""
__all__ = ["confirm_action", "notify_user"]

notify_user = print


def confirm_action(message: str) -> bool:
    """Basic (Y/n)? wrapper for `input`"""
    return input(message)[0:1] in "Yy"
