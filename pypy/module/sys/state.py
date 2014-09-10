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
        self._cleanup_()

    def _cleanup_(self):
        self.w_stdin = self.w_stdout = self.w_stderr = None

    def startup(self, space):
        if self.w_stdout is not None:
            return

        i, o, e = rfile.create_stdio()

        stdin = W_File(space)
        stdin.fdopenstream(i, "r", space.wrap("<stdin>"))
        self.w_stdin = space.wrap(stdin)

        stdout = W_File(space)
        stdout.fdopenstream(o, "w", space.wrap("<stdout>"))
        self.w_stdout = space.wrap(stdout)

        stderr = W_File(space)
        stderr.fdopenstream(e, "w", space.wrap("<stderr>"))
        self.w_stderr = space.wrap(stderr)

def getio(space):
    io = space.fromcache(IOState)
    io.startup(space)
    return io


def pypy_getudir(space):
    """NOT_RPYTHON
    (should be removed from interpleveldefs before translation)"""
    from rpython.tool.udir import udir
    return space.wrap(str(udir))
