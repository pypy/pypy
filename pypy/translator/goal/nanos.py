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

from pypy.interpreter.gateway import applevel, interp2app
import os, py

if os.name == 'posix':
    # code copied from posixpath.py
    app_os_path = applevel("""
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

        def normpath(path):
            if path == '':
                return '.'
            initial_slashes = path.startswith('/')
            # POSIX allows one or two initial slashes, but treats three or more
            # as single slash.
            if (initial_slashes and
                path.startswith('//') and not path.startswith('///')):
                initial_slashes = 2
            comps = path.split('/')
            new_comps = []
            for comp in comps:
                if comp in ('', '.'):
                    continue
                if (comp != '..' or (not initial_slashes and not new_comps) or
                     (new_comps and new_comps[-1] == '..')):
                    new_comps.append(comp)
                elif new_comps:
                    new_comps.pop()
            comps = new_comps
            path = '/'.join(comps)
            if initial_slashes:
                path = '/'*initial_slashes + path
            return path or '.'

        def abspath(path):
            if not path.startswith('/'):
                import posix
                cwd = posix.getcwd()
                path = join(cwd, path)
            return normpath(path)

        def isfile(path):
            import posix
            try:
                st = posix.stat(path)
            except posix.error:
                return False
            return (st.st_mode & 0170000) == 0100000      # S_ISREG

        def islink(path):
            import posix
            try:
                st = posix.lstat(path)
            except posix.error:
                return False
            return (st.st_mode & 0170000) == 0120000      # S_ISLNK

    """, filename=__file__)

    app_os = applevel("""
        sep = '/'
        pathsep = ':'
        name = 'posix'

        def readlink(fn):
            import posix
            return posix.readlink(fn)
    """, filename=__file__)

elif os.name == 'nt':
    # code copied from ntpath.py
    app_os_path = applevel(r"""
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

        def normpath(path):
            if path.startswith(('\\\\.\\', '\\\\?\\')):
                # in the case of paths with these prefixes:
                # \\.\ -> device names
                # \\?\ -> literal paths
                # do not do any normalization, but return the path unchanged
                return path
            path = path.replace('/', '\\')
            prefix, path = splitdrive(path)
            # We need to be careful here. If the prefix is empty, and
            # the path starts with a backslash, it could either be an
            # absolute path on the current drive (\dir1\dir2\file) or a
            # UNC filename (\\server\mount\dir1\file). It is therefore
            # imperative NOT to collapse multiple backslashes blindly in
            # that case.  The code below preserves multiple backslashes
            # when there is no drive letter. This means that the invalid
            # filename \\\a\b is preserved unchanged, where a\\\b is
            # normalised to a\b. It's not clear that there is any better
            # behaviour for such edge cases.
            if prefix == '':
                # No drive letter - preserve initial backslashes
                while path[:1] == "\\":
                    prefix = prefix + '\\'
                    path = path[1:]
            else:
                # We have a drive letter - collapse initial backslashes
                if path.startswith("\\"):
                    prefix = prefix + '\\'
                    path = path.lstrip("\\")
            comps = path.split("\\")
            i = 0
            while i < len(comps):
                if comps[i] in ('.', ''):
                    del comps[i]
                elif comps[i] == '..':
                    if i > 0 and comps[i-1] != '..':
                        del comps[i-1:i+1]
                        i -= 1
                    elif i == 0 and prefix.endswith("\\"):
                        del comps[i]
                    else:
                        i += 1
                else:
                    i += 1
            # If the path is now empty, substitute '.'
            if not prefix and not comps:
                comps.append('.')
            return prefix + '\\'.join(comps)

        def abspath(path):
            import nt
            if path: # Empty path must return current working directory.
                try:
                    path = nt._getfullpathname(path)
                except WindowsError:
                    pass # Bad path - return unchanged.
            else:
                path = nt.getcwd()
            return normpath(path)

        def isfile(path):
            import nt
            try:
                st = nt.stat(path)
            except nt.error:
                return False
            return (st.st_mode & 0170000) == 0100000      # S_ISREG

        def islink(path):
            return False

    """, filename=__file__)

    app_os = applevel(r"""
        sep = '\\'
        pathsep = ';'
        name = 'nt'
    """, filename=__file__)

else:
    raise NotImplementedError("os.name == %r" % (os.name,))

def getenv(space, w_name):
    name = space.str_w(w_name)
    return space.wrap(os.environ.get(name))
getenv_w = interp2app(getenv)

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

