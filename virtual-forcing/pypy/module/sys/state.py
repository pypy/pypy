"""
Implementation of interpreter-level 'sys' routines.
"""
import pypy
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import ObjSpace

import sys, os, stat, errno

# ____________________________________________________________
#

class State: 
    def __init__(self, space): 
        self.space = space 

        self.w_modules = space.newdict()

        self.w_warnoptions = space.newlist([])
        self.w_argv = space.newlist([])
        self.setinitialpath(space) 

    def setinitialpath(self, space): 
        # Initialize the default path
        pypydir = os.path.dirname(os.path.abspath(pypy.__file__))
        srcdir = os.path.dirname(pypydir)
        path = getinitialpath(srcdir)
        self.w_path = space.newlist([space.wrap(p) for p in path])

def checkdir(path):
    st = os.stat(path)
    if not stat.S_ISDIR(st[0]):
        raise OSError(errno.ENOTDIR, path)

def getinitialpath(srcdir):
    # build the initial path from the srcdir, which is the path of
    # the "dist" directory of a PyPy checkout.
    from pypy.module.sys.version import CPYTHON_VERSION

    dirname = '%d.%d.%d' % (CPYTHON_VERSION[0],
                            CPYTHON_VERSION[1],
                            CPYTHON_VERSION[2])
    lib_python = os.path.join(srcdir, 'lib-python')

    python_std_lib = os.path.join(lib_python, dirname)
    checkdir(python_std_lib)
    python_std_lib_modified = os.path.join(lib_python, 'modified-' + dirname)
    checkdir(python_std_lib_modified)
    pypydir = os.path.join(srcdir, 'pypy')
    pypy_lib = os.path.join(pypydir, 'lib')
    checkdir(pypy_lib)

    importlist = []
    importlist.append(pypy_lib)
    importlist.append(python_std_lib_modified)
    importlist.append(python_std_lib)
    return importlist

def pypy_initial_path(space, srcdir):
    try:
        path = getinitialpath(srcdir)
    except OSError:
        return space.w_None
    else:
        space.setitem(space.sys.w_dict, space.wrap('pypy_prefix'),
                                        space.wrap(srcdir))
        return space.newlist([space.wrap(p) for p in path])

pypy_initial_path.unwrap_spec = [ObjSpace, str]

def get(space):
    return space.fromcache(State)

class IOState:
    def __init__(self, space):
        from pypy.module._file.interp_file import W_File
        self.space = space

        stdin = W_File(space)
        stdin.file_fdopen(0, "r", 1)
        stdin.name = '<stdin>'
        self.w_stdin = space.wrap(stdin)

        stdout = W_File(space)
        stdout.file_fdopen(1, "w", 1)
        stdout.name = '<stdout>'
        self.w_stdout = space.wrap(stdout)

        stderr = W_File(space)
        stderr.file_fdopen(2, "w", 0)
        stderr.name = '<stderr>'
        self.w_stderr = space.wrap(stderr)

        stdin._when_reading_first_flush(stdout)

def getio(space):
    return space.fromcache(IOState)

def _pypy_getudir(space):
    """NOT_RPYTHON"""
    from pypy.tool.udir import udir
    return space.wrap(str(udir))
_pypy_getudir._annspecialcase_ = "override:ignore"

# we need the indirection because this function will live in a dictionary with other 
# RPYTHON functions and share call sites with them. Better it not be a special-case
# directly. 
def pypy_getudir(space):
    return _pypy_getudir(space)

