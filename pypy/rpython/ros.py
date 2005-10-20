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


class DIR(object):
    # a simulated DIR structure from C, i.e. a directory opened by
    # opendir() from which we can enumerate the entries with readdir().
    # Like readdir(), this version does not hide the '.' and '..' entries.
    def __init__(self, dirname):
        self._entries = iter(['.', '..'] + os.listdir(dirname))

    def readdir(self):
        try:
            return self._entries.next()
        except StopIteration:
            return None

    def closedir(self):
        pass

def opendir(dirname):
    return DIR(dirname)
