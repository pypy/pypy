"""
Helper file for Python equivalents of os specific calls.
"""

import os

def putenv(name_eq_value):
    # we fake it with the real one
    name, value = name_eq_value.split('=', 1)
    os.putenv(name, value)

_initial_items = os.environ.items()

def environ(idx):
    # we simulate the environ list
    if idx < len(_initial_items):
        return '%s=%s' % _initial_items[idx]
