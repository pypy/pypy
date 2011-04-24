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
        path = getinitialpath(srcdir)
        self.w_path = space.newlist([space.wrap(p) for p in path])

def checkdir(path):
    st = os.stat(path)
    if not stat.S_ISDIR(st[0]):
        raise OSError(errno.ENOTDIR, path)


platform = sys.platform

def getinitialpath(prefix):
    from pypy.module.sys.version import CPYTHON_VERSION
    dirname = '%d.%d.%d' % (CPYTHON_VERSION[0],
                            CPYTHON_VERSION[1],
                            CPYTHON_VERSION[2])
    lib_python = os.path.join(prefix, 'lib-python')
    python_std_lib = os.path.join(lib_python, dirname)
    checkdir(python_std_lib)
    python_std_lib_modified = os.path.join(lib_python, 'modified-' + dirname)
    checkdir(python_std_lib_modified)
    
    lib_pypy = os.path.join(prefix, 'lib_pypy')
    checkdir(lib_pypy)

    importlist = []
    importlist.append(lib_pypy)
    importlist.append(python_std_lib_modified)
    importlist.append(python_std_lib)
    #
    lib_tk_modified = os.path.join(python_std_lib_modified, 'lib-tk')
    lib_tk = os.path.join(python_std_lib, 'lib-tk')
    importlist.append(lib_tk_modified)
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

@unwrap_spec(srcdir=str)
def pypy_initial_path(space, srcdir):
    try:
        path = getinitialpath(srcdir)
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

def pypy_getudir(space):
    """NOT_RPYTHON
    (should be removed from interpleveldefs before translation)"""
    from pypy.tool.udir import udir
    return space.wrap(str(udir))
