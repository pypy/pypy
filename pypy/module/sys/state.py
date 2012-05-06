"""
Implementation of interpreter-level 'sys' routines.
"""
import pypy
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import unwrap_spec

import sys, os, stat, errno

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
        # Initialize the default path
        pypydir = os.path.dirname(os.path.abspath(pypy.__file__))
        srcdir = os.path.dirname(pypydir)
        path = getinitialpath(self, srcdir)
        self.w_path = space.newlist([space.wrap(p) for p in path])

def checkdir(path):
    st = os.stat(path)
    if not stat.S_ISDIR(st[0]):
        raise OSError(errno.ENOTDIR, path)


platform = sys.platform

def getinitialpath(state, prefix):
    from pypy.module.sys.version import CPYTHON_VERSION
    dirname = '%d.%d' % (CPYTHON_VERSION[0],
                         CPYTHON_VERSION[1])
    lib_python = os.path.join(prefix, 'lib-python')
    python_std_lib = os.path.join(lib_python, dirname)
    checkdir(python_std_lib)
    
    lib_pypy = os.path.join(prefix, 'lib_pypy')
    checkdir(lib_pypy)

    importlist = []
    #
    if state is not None:    # 'None' for testing only
        lib_extensions = os.path.join(lib_pypy, '__extensions__')
        state.w_lib_extensions = state.space.wrap(lib_extensions)
        importlist.append(lib_extensions)
    #
    importlist.append(lib_pypy)
    importlist.append(python_std_lib)
    #
    lib_tk = os.path.join(python_std_lib, 'lib-tk')
    importlist.append(lib_tk)
    #
    # List here the extra platform-specific paths.
    if platform != 'win32':
        importlist.append(os.path.join(python_std_lib, 'plat-'+platform))
    if platform == 'darwin':
        platmac = os.path.join(python_std_lib, 'plat-mac')
        importlist.append(platmac)
        importlist.append(os.path.join(platmac, 'lib-scriptpackages'))
    #
    return importlist

@unwrap_spec(srcdir='str0')
def pypy_initial_path(space, srcdir):
    try:
        path = getinitialpath(get(space), srcdir)
    except OSError:
        return space.w_None
    else:
        space.setitem(space.sys.w_dict, space.wrap('prefix'),
                                        space.wrap(srcdir))
        space.setitem(space.sys.w_dict, space.wrap('exec_prefix'),
                                        space.wrap(srcdir))
        return space.newlist([space.wrap(p) for p in path])

def get(space):
    return space.fromcache(State)

def pypy_getudir(space):
    """NOT_RPYTHON
    (should be removed from interpleveldefs before translation)"""
    from pypy.tool.udir import udir
    return space.wrap(str(udir))
