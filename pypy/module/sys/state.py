"""
Implementation of interpreter-level 'sys' routines.
"""
import os
import pypy

# ____________________________________________________________
#

class State:
    def __init__(self, space):
        self.space = space

        self.w_modules = space.newdict(module=True)
        self.w_warnoptions = space.newlist([])
        self.w_argv = space.newlist([])
        self.w_path = space.newlist([])

def get(space):
    return space.fromcache(State)

def pypy_getudir(space):
    """NOT_RPYTHON
    (should be removed from interpleveldefs before translation)"""
    from rpython.tool.udir import udir
    return space.wrap(str(udir))
