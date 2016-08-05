"""
Implementation of interpreter-level 'sys' routines.
"""
import os
from pypy import pypydir

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
        srcdir = os.path.dirname(pypydir)
        path = compute_stdlib_path(self, srcdir)
        self.w_path = space.newlist([space.wrap(p) for p in path])

def get(space):
    return space.fromcache(State)


class IOState:
    def __init__(self, space):
        from pypy.module._file.interp_file import W_File
        self.space = space

        stdin = W_File(space)
        stdin.file_fdopen(0, "r", 1)
        stdin.w_name = space.wrap('<stdin>')
        self.w_stdin = space.wrap(stdin)

        stdout = W_File(space)
        stdout.file_fdopen(1, "w", 1)
        stdout.w_name = space.wrap('<stdout>')
        self.w_stdout = space.wrap(stdout)

        stderr = W_File(space)
        stderr.file_fdopen(2, "w", 0)
        stderr.w_name = space.wrap('<stderr>')
        self.w_stderr = space.wrap(stderr)

        stdin._when_reading_first_flush(stdout)

def getio(space):
    return space.fromcache(IOState)


def pypy_getudir(space):
    """NOT_RPYTHON
    (should be removed from interpleveldefs before translation)"""
    from rpython.tool.udir import udir
    return space.wrap(str(udir))
