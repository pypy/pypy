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
    from pypy.rlib import ros

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

    #import pdb;pdb.set_trace()
    importlist = ['']
    pythonpath = ros.getenv('PYTHONPATH')
    if pythonpath:
        for p in pythonpath.split(os.pathsep):
            if p:
                importlist.append(p)
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
        return space.newlist([space.wrap(p) for p in path])

pypy_initial_path.unwrap_spec = [ObjSpace, str]

def get(space):
    return space.fromcache(State)

class IOState:
    def __init__(self, space):
        self.space = space

        w_fdopen = space.getattr(space.builtin.get('file'),
                                 space.wrap("fdopen"))
        self.w_stdin = space.call_function(
            w_fdopen, space.wrap(0), space.wrap("r"),
            space.wrap(1))
        space.setattr(self.w_stdin, space.wrap("_name"),
                      space.wrap("<stdin>"))
        self.w_stdout = space.call_function(
            w_fdopen, space.wrap(1), space.wrap("w"),
            space.wrap(1))
        space.setattr(self.w_stdout, space.wrap("_name"),
                      space.wrap("<stdout>"))
        self.w_stderr = space.call_function(
            w_fdopen, space.wrap(2), space.wrap("w"),
            space.wrap(0))
        space.setattr(self.w_stderr, space.wrap("_name"),
                      space.wrap("<stderr>"))

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

