"""
Logic to find sys.executable and the initial sys.path containing the stdlib
"""

import sys
import os
import stat
import errno
from pypy.rlib import rpath
from pypy.rlib.objectmodel import we_are_translated
from pypy.interpreter.gateway import unwrap_spec

platform = sys.platform
IS_WINDOWS = sys.platform == 'win32'

def find_executable(executable):
    if we_are_translated() and IS_WINDOWS and not executable.lower().endswith('.exe'):
        executable += '.exe'
    if os.sep in executable or (IS_WINDOWS and ':' in executable):
        pass    # the path is already more than just an executable name
    else:
        path = os.environ.get('PATH')
        if path:
            for dir in path.split(os.pathsep):
                fn = os.path.join(dir, executable)
                if os.path.isfile(fn):
                    executable = fn
                    break
    executable = rpath.rabspath(executable)
    #
    # 'sys.executable' should not end up being an non-existing file;
    # just use '' in this case. (CPython issue #7774)
    if not os.path.isfile(executable):
        executable = ''
    return executable



def checkdir(path):
    st = os.stat(path)
    if not stat.S_ISDIR(st[0]):
        raise OSError(errno.ENOTDIR, path)



def compute_stdlib_path(state, prefix):
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


@unwrap_spec(executable='str0')
def pypy_find_executable(space, executable):
    return space.wrap(find_executable(executable))


@unwrap_spec(srcdir='str0')
def pypy_initial_path(space, srcdir):
    try:
        path = compute_stdlib_path(get(space), srcdir)
    except OSError:
        return space.w_None
    else:
        space.setitem(space.sys.w_dict, space.wrap('prefix'),
                                        space.wrap(srcdir))
        space.setitem(space.sys.w_dict, space.wrap('exec_prefix'),
                                        space.wrap(srcdir))
        return space.newlist([space.wrap(p) for p in path])


