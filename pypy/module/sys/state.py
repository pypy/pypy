"""
Implementation of interpreter-level 'sys' routines.
"""
import os
import pypy

from rpython.rlib import rfile
from pypy.module._file.interp_file import W_File

# ____________________________________________________________
#

class State:
    def __init__(self, space):
        self.space = space

        self.w_modules = space.newdict(module=True)
        self.w_warnoptions = space.newlist([])
        self.w_argv = space.newlist([])

        self.setinitialpath(space)

    def setinitialpath(self, space):
        from pypy.module.sys.initpath import compute_stdlib_path
        # Initialize the default path
        pypydir = os.path.dirname(os.path.abspath(pypy.__file__))
        srcdir = os.path.dirname(pypydir)
        path = compute_stdlib_path(self, srcdir)
        self.w_path = space.newlist([space.wrap(p) for p in path])

def get(space):
    return space.fromcache(State)


class IOState:
    def __init__(self, space):
        pass

    def startup(self, space):
        i, o, e = rfile.create_stdio()

        stdin = W_File(space)
        stdin.fdopenstream(i, "r", space.wrap("<stdin>"))
        self.stdin = stdin

        stdout = W_File(space)
        stdout.fdopenstream(o, "w", space.wrap("<stdout>"))
        self.stdout = stdout

        stderr = W_File(space)
        stderr.fdopenstream(e, "w", space.wrap("<stderr>"))
        self.stderr = stderr

def getio(space):
    return space.fromcache(IOState)


def pypy_getudir(space):
    """NOT_RPYTHON
    (should be removed from interpleveldefs before translation)"""
    from rpython.tool.udir import udir
    return space.wrap(str(udir))
