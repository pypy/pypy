"""
This file defines utilities for manipulating objects in an
RPython-compliant way.
"""

import new


def instantiate(cls):
    "Create an empty instance of 'cls'."
    if isinstance(cls, type):
        return object.__new__(cls)
    else:
        return new.instance(cls)
