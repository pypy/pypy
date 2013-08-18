"""
Logic to find sys.executable and the initial sys.path containing the stdlib
"""

import sys
import os
import stat
import errno
from rpython.rlib import rpath
from rpython.rlib.objectmodel import we_are_translated
from pypy.interpreter.gateway import unwrap_spec
from pypy.module.sys.state import get as get_state

platform = sys.platform
IS_WINDOWS = sys.platform == 'win32'

def find_executable(executable):
    """
    Return the absolute path of the executable, by looking into PATH and the
    current directory.  If it cannot be found, return ''.
    """
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

    # 'sys.executable' should not end up being an non-existing file;
    # just use '' in this case. (CPython issue #7774)
    if not os.path.isfile(executable):
        executable = ''
    return executable

def _readlink_maybe(filename):
    if not IS_WINDOWS:
        return os.readlink(filename)
    raise NotImplementedError

def resolvedirof(filename):
    filename = rpath.rabspath(filename)
    dirname = rpath.rabspath(os.path.join(filename, '..'))
    if os.path.islink(filename):
        try:
            link = _readlink_maybe(filename)
        except OSError:
            pass
        else:
            return resolvedirof(os.path.join(dirname, link))
    return dirname

def find_stdlib(state, executable):
    """
    Find and compute the stdlib path, starting from the directory where
    ``executable`` is and going one level up until we find it.  Return a tuple
    (path, prefix), where ``prefix`` is the root directory which contains the
    stdlib.
    If it cannot be found, return (None, None).
    """
    if executable == '':
        executable = 'pypy-c'
    search = executable
    while True:
        dirname = resolvedirof(search)
        if dirname == search:
            return None, None # not found :-(
        newpath = compute_stdlib_path_maybe(state, dirname)
        if newpath is not None:
            return newpath, dirname
        search = dirname    # walk to the parent directory

def _checkdir(path):
    st = os.stat(path)
    if not stat.S_ISDIR(st[0]):
        raise OSError(errno.ENOTDIR, path)

def compute_stdlib_path(state, prefix):
    """
    Compute the paths for the stdlib rooted at ``prefix``. ``prefix`` must at
    least contain a directory called ``lib-python/X.Y`` and another one called
    ``lib_pypy``. If they cannot be found, it raises OSError.
    """
    from pypy.module.sys.version import CPYTHON_VERSION
    dirname = '%d.%d' % (CPYTHON_VERSION[0],
                         CPYTHON_VERSION[1])
    lib_python = os.path.join(prefix, 'lib-python')
    python_std_lib = os.path.join(lib_python, dirname)
    _checkdir(python_std_lib)

    lib_pypy = os.path.join(prefix, 'lib_pypy')
    _checkdir(lib_pypy)

    importlist = []

    if state is not None:    # 'None' for testing only
        lib_extensions = os.path.join(lib_pypy, '__extensions__')
        state.w_lib_extensions = state.space.wrap(lib_extensions)
        importlist.append(lib_extensions)

    importlist.append(lib_pypy)
    importlist.append(python_std_lib)

    lib_tk = os.path.join(python_std_lib, 'lib-tk')
    importlist.append(lib_tk)

    # List here the extra platform-specific paths.
    if platform != 'win32':
        importlist.append(os.path.join(python_std_lib, 'plat-'+platform))
    if platform == 'darwin':
        platmac = os.path.join(python_std_lib, 'plat-mac')
        importlist.append(platmac)
        importlist.append(os.path.join(platmac, 'lib-scriptpackages'))

    return importlist

def compute_stdlib_path_maybe(state, prefix):
    """
    Return the stdlib path rooted at ``prefix``, or None if it cannot be
    found.
    """
    try:
        return compute_stdlib_path(state, prefix)
    except OSError:
        return None

@unwrap_spec(executable='str0')
def pypy_find_executable(space, executable):
    return space.wrap(find_executable(executable))

@unwrap_spec(filename='str0')
def pypy_resolvedirof(space, filename):
    return space.wrap(resolvedirof(filename))

@unwrap_spec(executable='str0')
def pypy_find_stdlib(space, executable):
    path, prefix = find_stdlib(get_state(space), executable)
    if path is None:
        return space.w_None
    else:
        space.setitem(space.sys.w_dict, space.wrap('prefix'),
                                        space.wrap(prefix))
        space.setitem(space.sys.w_dict, space.wrap('exec_prefix'),
                                        space.wrap(prefix))
        return space.newlist([space.wrap(p) for p in path])
