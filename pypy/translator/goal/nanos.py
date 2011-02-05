"""
Not An os or Nano os :-)

Implementation of a few methods needed for starting up
PyPy in app_main without importing os there.

At startup time, app_main wants to find out about itself,
sys.executable, the path to its library etc.
This is done the easiest using os.py, but since this
is a python module, we have a recurrence problem.

Importing it at compile time would work, partially,
but the way os is initialized will cause os.getenv
to malfunction, due to caching problems.

The solution taken here implements a minimal os using
app-level code that is created at compile-time. Only
the few needed functions are implemented in a tiny os module
that contains a tiny path module.

os.getenv got a direct implementation to overcome the caching
problem.

Please adjust the applevel code below, if you need to support
more from os and os.path.
"""

from pypy.interpreter.gateway import applevel, ObjSpace, W_Root, interp2app
import os, py

if os.name == 'posix':
    # code copied from posixpath.py
    app_os_path = applevel("""
        from posix import getcwd, stat, lstat, error

        def dirname(p):
            i = p.rfind('/') + 1
            head = p[:i]
            if head and head != '/'*len(head):
                head = head.rstrip('/')
            return head

        def join(path, b):
            if b.startswith('/'):
                path = b
            elif path == '' or path.endswith('/'):
                path +=  b
            else:
                path += '/' + b
            return path

        def abspath(path):
            if not path.startswith('/'):
                cwd = getcwd()
                path = join(cwd, path)
            return path       # this version does not call normpath()!

        def isfile(path):
            try:
                st = stat(path)
            except error:
                return False
            return (st.st_mode & 0170000) == 0100000      # S_ISREG

        def islink(path):
            try:
                st = lstat(path)
            except error:
                return False
            return (st.st_mode & 0170000) == 0120000      # S_ISLNK

    """, filename=__file__)

    app_os = applevel("""
        sep = '/'
        pathsep = ':'
        name = 'posix'
        from posix import fdopen, readlink
    """, filename=__file__)

elif os.name == 'nt':
    # code copied from ntpath.py
    app_os_path = applevel("""
        from nt import _getfullpathname, getcwd, stat, lstat, error

        def splitdrive(p):
            if p[1:2] == ':':
                return p[0:2], p[2:]
            return '', p

        def isabs(s):
            s = splitdrive(s)[1]
            return s != '' and s[:1] in '/\\'

        def dirname(p):
            d, p = splitdrive(p)
            # set i to index beyond p's last slash
            i = len(p)
            while i and p[i-1] not in '/\\':
                i = i - 1
            head = p[:i]
            # remove trailing slashes from head, unless it's all slashes
            head2 = head
            while head2 and head2[-1] in '/\\':
                head2 = head2[:-1]
            head = head2 or head
            return d + head

        def join(path, b):
            b_wins = 0  # set to 1 iff b makes path irrelevant
            if path == "":
                b_wins = 1

            elif isabs(b):
                # This probably wipes out path so far.  However, it's more
                # complicated if path begins with a drive letter:
                #     1. join('c:', '/a') == 'c:/a'
                #     2. join('c:/', '/a') == 'c:/a'
                # But
                #     3. join('c:/a', '/b') == '/b'
                #     4. join('c:', 'd:/') = 'd:/'
                #     5. join('c:/', 'd:/') = 'd:/'
                if path[1:2] != ":" or b[1:2] == ":":
                    # Path doesn't start with a drive letter, or cases 4 and 5.
                    b_wins = 1

                # Else path has a drive letter, and b doesn't but is absolute.
                elif len(path) > 3 or (len(path) == 3 and
                                       path[-1] not in "/\\"):
                    # case 3
                    b_wins = 1

            if b_wins:
                path = b
            else:
                # Join, and ensure there's a separator.
                assert len(path) > 0
                if path[-1] in "/\\":
                    if b and b[0] in "/\\":
                        path += b[1:]
                    else:
                        path += b
                elif path[-1] == ":":
                    path += b
                elif b:
                    if b[0] in "/\\":
                        path += b
                    else:
                        path += "\\" + b
                else:
                    # path is not empty and does not end with a backslash,
                    # but b is empty; since, e.g., split('a/') produces
                    # ('a', ''), it's best if join() adds a backslash in
                    # this case.
                    path += '\\'

            return path

        def abspath(path):
            if path: # Empty path must return current working directory.
                try:
                    path = _getfullpathname(path)
                except WindowsError:
                    pass # Bad path - return unchanged.
            else:
                path = getcwd()
            return path       # this version does not call normpath()!

        def isfile(path):
            try:
                st = stat(path)
            except error:
                return False
            return (st.st_mode & 0170000) == 0100000      # S_ISREG

        def islink(path):
            return False

    """, filename=__file__)

    app_os = applevel("""
        sep = '\\'
        pathsep = ';'
        name = 'nt'
        from posix import fdopen
    """, filename=__file__)

else:
    raise NotImplementedError("os.name == %r" % (os.name,))

def getenv(space, w_name):
    name = space.str_w(w_name)
    return space.wrap(os.environ.get(name))
getenv_w = interp2app(getenv, unwrap_spec=[ObjSpace, W_Root])

def setup_nanos(space):
    w_os = space.wrap(app_os.buildmodule(space, 'os'))
    w_os_path = space.wrap(app_os_path.buildmodule(space, 'path'))
    space.setattr(w_os, space.wrap('path'), w_os_path)
    space.setattr(w_os, space.wrap('getenv'), space.wrap(getenv_w))
    return w_os


# in order to be able to test app_main without the pypy interpreter
# we create the nanos module with the same names here like it would
# be created while translation
path_module_for_testing = type(os)("os.path")
os_module_for_testing = type(os)("os")
os_module_for_testing.path = path_module_for_testing
os_module_for_testing.getenv = os.getenv
eval(py.code.Source(app_os_path.source).compile(), path_module_for_testing.__dict__)
eval(py.code.Source(app_os.source).compile(), os_module_for_testing.__dict__)

