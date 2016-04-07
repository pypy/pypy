import os
import sys
from math import modf
from errno import EOPNOTSUPP
try:
    from errno import ENOTSUP
except ImportError:
    # some Pythons don't have errno.ENOTSUP
    ENOTSUP = 0

from rpython.rlib import rposix, rposix_stat
from rpython.rlib import objectmodel, rurandom
from rpython.rlib.objectmodel import specialize
from rpython.rlib.rarithmetic import r_longlong, intmask
from rpython.rlib.unroll import unrolling_iterable

from pypy.interpreter.gateway import (
    unwrap_spec, WrappedDefault, Unwrapper, kwonly)
from pypy.interpreter.error import (
    OperationError, wrap_oserror, oefmt, wrap_oserror2, strerror as _strerror)
from pypy.interpreter.executioncontext import ExecutionContext


_WIN32 = sys.platform == 'win32'
if _WIN32:
    from rpython.rlib import rwin32

c_int = "c_int"

# CPython 2.7 semantics are too messy to follow exactly,
# e.g. setuid(-2) works on 32-bit but not on 64-bit.  As a result,
# we decided to just accept any 'int', i.e. any C signed long, and
# check that they are in range(-2**31, 2**32).  In other words, we
# accept any number that is either a signed or an unsigned C int.
c_uid_t = int
c_gid_t = int
if sys.maxint == 2147483647:
    def check_uid_range(space, num):
        pass
else:
    def check_uid_range(space, num):
        if num < -(1 << 31) or num >= (1 << 32):
            raise OperationError(space.w_OverflowError,
                                 space.wrap("integer out of range"))

class FileEncoder(object):
    is_unicode = True

    def __init__(self, space, w_obj):
        self.space = space
        self.w_obj = w_obj

    def as_bytes(self):
        return self.space.fsencode_w(self.w_obj)

    def as_unicode(self):
        return self.space.unicode0_w(self.w_obj)

class FileDecoder(object):
    is_unicode = False

    def __init__(self, space, w_obj):
        self.space = space
        self.w_obj = w_obj

    def as_bytes(self):
        return self.space.bytes0_w(self.w_obj)

    def as_unicode(self):
        return self.space.fsdecode_w(self.w_obj)

@specialize.memo()
def make_dispatch_function(func, tag, allow_fd_fn=None):
    def dispatch(space, w_fname, *args):
        if allow_fd_fn is not None:
            try:
                fd = space.c_int_w(w_fname)
            except OperationError:
                pass
            else:
                return allow_fd_fn(fd, *args)
        if space.isinstance_w(w_fname, space.w_unicode):
            fname = FileEncoder(space, w_fname)
            return func(fname, *args)
        else:
            fname = space.bytes0_w(w_fname)
            return func(fname, *args)
    return dispatch

@specialize.arg(0, 1)
def dispatch_filename(func, tag=0, allow_fd_fn=None):
    return make_dispatch_function(func, tag, allow_fd_fn)

@specialize.memo()
def dispatch_filename_2(func):
    def dispatch(space, w_fname1, w_fname2, *args):
        if space.isinstance_w(w_fname1, space.w_unicode):
            fname1 = FileEncoder(space, w_fname1)
            if space.isinstance_w(w_fname2, space.w_unicode):
                fname2 = FileEncoder(space, w_fname2)
                return func(fname1, fname2, *args)
            else:
                fname2 = FileDecoder(space, w_fname2)
                return func(fname1, fname2, *args)
        else:
            fname1 = FileDecoder(space, w_fname1)
            if space.isinstance_w(w_fname2, space.w_unicode):
                fname2 = FileEncoder(space, w_fname2)
                return func(fname1, fname2, *args)
            else:
                fname2 = FileDecoder(space, w_fname2)
                return func(fname1, fname2, *args)
    return dispatch


if hasattr(rposix, 'AT_FDCWD'):
    DEFAULT_DIR_FD = rposix.AT_FDCWD
else:
    DEFAULT_DIR_FD = -100
DIR_FD_AVAILABLE = False

def unwrap_fd(space, w_value):
    return space.c_int_w(w_value)

def _unwrap_dirfd(space, w_value):
    if space.is_none(w_value):
        return DEFAULT_DIR_FD
    else:
        return unwrap_fd(space, w_value)

class _DirFD(Unwrapper):
    def unwrap(self, space, w_value):
        return _unwrap_dirfd(space, w_value)

class _DirFD_Unavailable(Unwrapper):
    def unwrap(self, space, w_value):
        dir_fd = unwrap_fd(space, w_value)
        if dir_fd == DEFAULT_DIR_FD:
            return dir_fd
        else:
            raise oefmt(
                space.w_NotImplementedError,
                "dir_fd unavailable on this platform")

def DirFD(available=False):
    return _DirFD if available else _DirFD_Unavailable

@specialize.arg(1, 2)
def argument_unavailable(space, funcname, arg):
    return oefmt(
            space.w_NotImplementedError,
            "%s: %s unavailable on this platform", funcname, arg)

@unwrap_spec(flags=c_int, mode=c_int, dir_fd=DirFD(rposix.HAVE_OPENAT))
def open(space, w_path, flags, mode=0777, dir_fd=DEFAULT_DIR_FD):
    """open(path, flags, mode=0o777, *, dir_fd=None)

Open a file for low level IO.  Returns a file handle (integer).

If dir_fd is not None, it should be a file descriptor open to a directory,
  and path should be relative; path will then be relative to that directory.
dir_fd may not be implemented on your platform.
  If it is unavailable, using it will raise a NotImplementedError."""
    try:
        if dir_fd == DEFAULT_DIR_FD:
            fd = dispatch_filename(rposix.open)(space, w_path, flags, mode)
        else:
            path = space.fsencode_w(w_path)
            fd = rposix.openat(path, flags, mode, dir_fd)
    except OSError as e:
        raise wrap_oserror2(space, e, w_path)
    return space.wrap(fd)

@unwrap_spec(fd=c_int, pos=r_longlong, how=c_int)
def lseek(space, fd, pos, how):
    """Set the current position of a file descriptor.  Return the new position.
If how == 0, 'pos' is relative to the start of the file; if how == 1, to the
current position; if how == 2, to the end."""
    try:
        pos = os.lseek(fd, pos, how)
    except OSError, e:
        raise wrap_oserror(space, e)
    else:
        return space.wrap(pos)

@unwrap_spec(fd=c_int)
def isatty(space, fd):
    """Return True if 'fd' is an open file descriptor connected to the
slave end of a terminal."""
    try:
        res = os.isatty(fd)
    except OSError, e:
        raise wrap_oserror(space, e)
    else:
        return space.wrap(res)

@unwrap_spec(fd=c_int, buffersize=int)
def read(space, fd, buffersize):
    """Read data from a file descriptor."""
    try:
        s = os.read(fd, buffersize)
    except OSError, e:
        raise wrap_oserror(space, e)
    else:
        return space.wrapbytes(s)

@unwrap_spec(fd=c_int)
def write(space, fd, w_data):
    """Write a string to a file descriptor.  Return the number of bytes
actually written, which may be smaller than len(data)."""
    data = space.getarg_w('y*', w_data)
    try:
        res = os.write(fd, data.as_str())
    except OSError, e:
        raise wrap_oserror(space, e)
    else:
        return space.wrap(res)

@unwrap_spec(fd=c_int)
def close(space, fd):
    """Close a file descriptor (for low level IO)."""
    try:
        os.close(fd)
    except OSError, e:
        raise wrap_oserror(space, e)

@unwrap_spec(fd_low=c_int, fd_high=c_int)
def closerange(fd_low, fd_high):
    """Closes all file descriptors in [fd_low, fd_high), ignoring errors."""
    rposix.closerange(fd_low, fd_high)

@unwrap_spec(fd=c_int, length=r_longlong)
def ftruncate(space, fd, length):
    """Truncate a file (by file descriptor) to a specified length."""
    try:
        os.ftruncate(fd, length)
    except IOError, e:
        if not objectmodel.we_are_translated():
            # Python 2.6 raises an IOError here. Let's not repeat that mistake.
            w_error = space.call_function(space.w_OSError, space.wrap(e.errno),
                                          space.wrap(e.strerror),
                                          space.wrap(e.filename))
            raise OperationError(space.w_OSError, w_error)
        raise AssertionError
    except OSError, e:
        raise wrap_oserror(space, e)

def truncate(space, w_path, w_length):
    """Truncate a file to a specified length."""
    allocated_fd = False
    fd = -1
    try:
        if space.isinstance_w(w_path, space.w_int):
            w_fd = w_path
        else:
            w_fd = open(space, w_path, os.O_RDWR | os.O_CREAT)
            allocated_fd = True

        fd = space.c_filedescriptor_w(w_fd)
        length = space.int_w(w_length)
        return ftruncate(space, fd, length)

    finally:
        if allocated_fd and fd != -1:
            close(space, fd)

def fsync(space, w_fd):
    """Force write of file with filedescriptor to disk."""
    fd = space.c_filedescriptor_w(w_fd)
    try:
        os.fsync(fd)
    except OSError, e:
        raise wrap_oserror(space, e)

def fdatasync(space, w_fd):
    """Force write of file with filedescriptor to disk.
Does not force update of metadata."""
    fd = space.c_filedescriptor_w(w_fd)
    try:
        os.fdatasync(fd)
    except OSError, e:
        raise wrap_oserror(space, e)

def fchdir(space, w_fd):
    """Change to the directory of the given file descriptor.  fildes must be
opened on a directory, not a file."""
    fd = space.c_filedescriptor_w(w_fd)
    try:
        os.fchdir(fd)
    except OSError, e:
        raise wrap_oserror(space, e)

# ____________________________________________________________

STAT_FIELDS = unrolling_iterable(enumerate(rposix_stat.STAT_FIELDS))

STATVFS_FIELDS = unrolling_iterable(enumerate(rposix_stat.STATVFS_FIELDS))

def build_stat_result(space, st):
    FIELDS = STAT_FIELDS    # also when not translating at all
    lst = [None] * rposix_stat.N_INDEXABLE_FIELDS
    w_keywords = space.newdict()
    stat_float_times = space.fromcache(StatState).stat_float_times
    for i, (name, TYPE) in FIELDS:
        value = getattr(st, name)
        if name in ('st_atime', 'st_mtime', 'st_ctime'):
            value = int(value)   # rounded to an integer for indexed access
        w_value = space.wrap(value)
        if i < rposix_stat.N_INDEXABLE_FIELDS:
            lst[i] = w_value
        else:
            space.setitem(w_keywords, space.wrap(name), w_value)

    # non-rounded values for name-based access
    if stat_float_times:
        space.setitem(w_keywords,
                      space.wrap('st_atime'), space.wrap(st.st_atime))
        space.setitem(w_keywords,
                      space.wrap('st_mtime'), space.wrap(st.st_mtime))
        space.setitem(w_keywords,
                      space.wrap('st_ctime'), space.wrap(st.st_ctime))
    else:
        space.setitem(w_keywords,
                      space.wrap('st_atime'), space.wrap(int(st.st_atime)))
        space.setitem(w_keywords,
                      space.wrap('st_mtime'), space.wrap(int(st.st_mtime)))
        space.setitem(w_keywords,
                      space.wrap('st_ctime'), space.wrap(int(st.st_ctime)))

    w_tuple = space.newtuple(lst)
    w_stat_result = space.getattr(space.getbuiltinmodule(os.name),
                                  space.wrap('stat_result'))
    return space.call_function(w_stat_result, w_tuple, w_keywords)


def build_statvfs_result(space, st):
    vals_w = [None] * len(rposix_stat.STATVFS_FIELDS)
    for i, (name, _) in STATVFS_FIELDS:
        vals_w[i] = space.wrap(getattr(st, name))
    w_tuple = space.newtuple(vals_w)
    w_statvfs_result = space.getattr(
        space.getbuiltinmodule(os.name), space.wrap('statvfs_result'))
    return space.call_function(w_statvfs_result, w_tuple)


@unwrap_spec(fd=c_int)
def fstat(space, fd):
    """Perform a stat system call on the file referenced to by an open
file descriptor."""
    try:
        st = rposix_stat.fstat(fd)
    except OSError, e:
        raise wrap_oserror(space, e)
    else:
        return build_stat_result(space, st)

@unwrap_spec(dir_fd=DirFD(rposix.HAVE_FSTATAT), follow_symlinks=kwonly(bool))
def stat(space, w_path, dir_fd=DEFAULT_DIR_FD, follow_symlinks=True):
    """stat(path, *, dir_fd=None, follow_symlinks=True) -> stat result

Perform a stat system call on the given path.

path may be specified as either a string or as an open file descriptor.

If dir_fd is not None, it should be a file descriptor open to a directory,
  and path should be relative; path will then be relative to that directory.
  dir_fd may not be supported on your platform; if it is unavailable, using
  it will raise a NotImplementedError.
If follow_symlinks is False, and the last element of the path is a symbolic
  link, stat will examine the symbolic link itself instead of the file the
  link points to.
It is an error to use dir_fd or follow_symlinks when specifying path as
  an open file descriptor."""
    if follow_symlinks and dir_fd == DEFAULT_DIR_FD:
        try:
            st = dispatch_filename(rposix_stat.stat, 0,
                                allow_fd_fn=rposix_stat.fstat)(space, w_path)
        except OSError as e:
            raise wrap_oserror2(space, e, w_path)
        else:
            return build_stat_result(space, st)

    if not follow_symlinks and dir_fd == DEFAULT_DIR_FD:
        return lstat(space, w_path)

    if rposix.HAVE_FSTATAT:
        try:
            path = space.fsencode_w(w_path)
            st = rposix_stat.fstatat(path, dir_fd, follow_symlinks)
        except OSError as e:
            raise wrap_oserror2(space, e, w_path)
        return build_stat_result(space, st)

    raise oefmt(space.w_NotImplementedError,
        "stat: unsupported argument combination")

@unwrap_spec(dir_fd=DirFD(available=False))
def lstat(space, w_path, dir_fd=DEFAULT_DIR_FD):
    """lstat(path, *, dir_fd=None) -> stat result

Like stat(), but do not follow symbolic links.
Equivalent to stat(path, follow_symlinks=False)."""

    try:
        st = dispatch_filename(rposix_stat.lstat)(space, w_path)
    except OSError, e:
        raise wrap_oserror2(space, e, w_path)
    else:
        return build_stat_result(space, st)

class StatState(object):
    def __init__(self, space):
        self.stat_float_times = True

def stat_float_times(space, w_value=None):
    """stat_float_times([newval]) -> oldval

Determine whether os.[lf]stat represents time stamps as float objects.
If newval is True, future calls to stat() return floats, if it is False,
future calls return ints.
If newval is omitted, return the current setting.
"""
    state = space.fromcache(StatState)

    if w_value is None:
        return space.wrap(state.stat_float_times)
    else:
        state.stat_float_times = space.bool_w(w_value)


@unwrap_spec(fd=c_int)
def fstatvfs(space, fd):
    try:
        st = rposix_stat.fstatvfs(fd)
    except OSError as e:
        raise wrap_oserror(space, e)
    else:
        return build_statvfs_result(space, st)


def statvfs(space, w_path):
    """statvfs(path)

Perform a statvfs system call on the given path.

path may always be specified as a string.
On some platforms, path may also be specified as an open file descriptor.
  If this functionality is unavailable, using it raises an exception."""
    try:
        st = dispatch_filename(
            rposix_stat.statvfs,
            allow_fd_fn=rposix_stat.fstatvfs)(space, w_path)
    except OSError as e:
        raise wrap_oserror2(space, e, w_path)
    else:
        return build_statvfs_result(space, st)


@unwrap_spec(fd=c_int)
def dup(space, fd):
    """Create a copy of the file descriptor.  Return the new file
descriptor."""
    try:
        newfd = os.dup(fd)
    except OSError, e:
        raise wrap_oserror(space, e)
    else:
        return space.wrap(newfd)

@unwrap_spec(old_fd=c_int, new_fd=c_int)
def dup2(space, old_fd, new_fd):
    """Duplicate a file descriptor."""
    try:
        os.dup2(old_fd, new_fd)
    except OSError, e:
        raise wrap_oserror(space, e)

@unwrap_spec(mode=c_int,
    dir_fd=DirFD(rposix.HAVE_FACCESSAT), effective_ids=kwonly(bool), follow_symlinks=kwonly(bool))
def access(space, w_path, mode,
        dir_fd=DEFAULT_DIR_FD, effective_ids=True, follow_symlinks=True):
    """\
access(path, mode, *, dir_fd=None, effective_ids=False, follow_symlinks=True)

Use the real uid/gid to test for access to a path.  Returns True if granted,
False otherwise.

If dir_fd is not None, it should be a file descriptor open to a directory,
  and path should be relative; path will then be relative to that directory.
If effective_ids is True, access will use the effective uid/gid instead of
  the real uid/gid.
If follow_symlinks is False, and the last element of the path is a symbolic
  link, access will examine the symbolic link itself instead of the file the
  link points to.
dir_fd, effective_ids, and follow_symlinks may not be implemented
  on your platform.  If they are unavailable, using them will raise a
  NotImplementedError.

Note that most operations will use the effective uid/gid, therefore this
  routine can be used in a suid/sgid environment to test if the invoking user
  has the specified access to the path.
The mode argument can be F_OK to test existence, or the inclusive-OR
  of R_OK, W_OK, and X_OK."""
    if not rposix.HAVE_FACCESSAT:
        if not follow_symlinks:
            raise argument_unavailable(space, "access", "follow_symlinks")
        if effective_ids:
            raise argument_unavailable(space, "access", "effective_ids")

    try:
        if dir_fd == DEFAULT_DIR_FD and follow_symlinks and not effective_ids:
            ok = dispatch_filename(rposix.access)(space, w_path, mode)
        else:
            path = space.fsencode_w(w_path)
            ok = rposix.faccessat(path, mode,
                dir_fd, effective_ids, follow_symlinks)
    except OSError as e:
        raise wrap_oserror2(space, e, w_path)
    else:
        return space.wrap(ok)


def times(space):
    """
    times() -> (utime, stime, cutime, cstime, elapsed_time)

    Return a tuple of floating point numbers indicating process times.
    """
    try:
        times = os.times()
    except OSError, e:
        raise wrap_oserror(space, e)
    else:
        return space.newtuple([space.wrap(times[0]),
                               space.wrap(times[1]),
                               space.wrap(times[2]),
                               space.wrap(times[3]),
                               space.wrap(times[4])])

@unwrap_spec(cmd='fsencode')
def system(space, cmd):
    """Execute the command (a string) in a subshell."""
    try:
        rc = os.system(cmd)
    except OSError, e:
        raise wrap_oserror(space, e)
    else:
        return space.wrap(rc)

@unwrap_spec(dir_fd=DirFD(rposix.HAVE_UNLINKAT))
def unlink(space, w_path, dir_fd=DEFAULT_DIR_FD):
    """unlink(path, *, dir_fd=None)

Remove a file (same as remove()).

If dir_fd is not None, it should be a file descriptor open to a directory,
  and path should be relative; path will then be relative to that directory.
dir_fd may not be implemented on your platform.
  If it is unavailable, using it will raise a NotImplementedError."""
    try:
        if dir_fd == DEFAULT_DIR_FD:
            dispatch_filename(rposix.unlink)(space, w_path)
        else:
            path = space.fsencode_w(w_path)
            rposix.unlinkat(path, dir_fd, removedir=False)
    except OSError as e:
        raise wrap_oserror2(space, e, w_path)

@unwrap_spec(dir_fd=DirFD(rposix.HAVE_UNLINKAT))
def remove(space, w_path, dir_fd=DEFAULT_DIR_FD):
    """remove(path, *, dir_fd=None)

Remove a file (same as unlink()).

If dir_fd is not None, it should be a file descriptor open to a directory,
  and path should be relative; path will then be relative to that directory.
dir_fd may not be implemented on your platform.
  If it is unavailable, using it will raise a NotImplementedError."""
    try:
        if dir_fd == DEFAULT_DIR_FD:
            dispatch_filename(rposix.unlink)(space, w_path)
        else:
            path = space.fsencode_w(w_path)
            rposix.unlinkat(path, dir_fd, removedir=False)
    except OSError as e:
        raise wrap_oserror2(space, e, w_path)

def _getfullpathname(space, w_path):
    """helper for ntpath.abspath """
    try:
        if space.isinstance_w(w_path, space.w_unicode):
            path = FileEncoder(space, w_path)
            fullpath = rposix.getfullpathname(path)
            w_fullpath = space.wrap(fullpath)
        else:
            path = space.str0_w(w_path)
            fullpath = rposix.getfullpathname(path)
            w_fullpath = space.wrapbytes(fullpath)
    except OSError, e:
        raise wrap_oserror2(space, e, w_path)
    else:
        return w_fullpath

def getcwdb(space):
    """Return the current working directory."""
    try:
        cur = os.getcwd()
    except OSError, e:
        raise wrap_oserror(space, e)
    else:
        return space.wrapbytes(cur)

if _WIN32:
    def getcwd(space):
        """Return the current working directory as a string."""
        try:
            cur = os.getcwdu()
        except OSError, e:
            raise wrap_oserror(space, e)
        else:
            return space.wrap(cur)
else:
    def getcwd(space):
        """Return the current working directory as a string."""
        return space.fsdecode(getcwdb(space))

def chdir(space, w_path):
    """Change the current working directory to the specified path."""
    try:
        dispatch_filename(rposix.chdir)(space, w_path)
    except OSError, e:
        raise wrap_oserror2(space, e, w_path)

@unwrap_spec(mode=c_int, dir_fd=DirFD(rposix.HAVE_MKDIRAT))
def mkdir(space, w_path, mode=0o777, dir_fd=DEFAULT_DIR_FD):
    """mkdir(path, mode=0o777, *, dir_fd=None)

Create a directory.

If dir_fd is not None, it should be a file descriptor open to a directory,
  and path should be relative; path will then be relative to that directory.
dir_fd may not be implemented on your platform.
  If it is unavailable, using it will raise a NotImplementedError.

The mode argument is ignored on Windows."""
    try:
        if dir_fd == DEFAULT_DIR_FD:
            dispatch_filename(rposix.mkdir)(space, w_path, mode)
        else:
            path = space.fsencode_w(w_path)
            rposix.mkdirat(path, mode, dir_fd)
    except OSError as e:
        raise wrap_oserror2(space, e, w_path)

@unwrap_spec(dir_fd=DirFD(rposix.HAVE_UNLINKAT))
def rmdir(space, w_path, dir_fd=DEFAULT_DIR_FD):
    """rmdir(path, *, dir_fd=None)

Remove a directory.

If dir_fd is not None, it should be a file descriptor open to a directory,
  and path should be relative; path will then be relative to that directory.
dir_fd may not be implemented on your platform.
  If it is unavailable, using it will raise a NotImplementedError."""
    try:
        if dir_fd == DEFAULT_DIR_FD:
            dispatch_filename(rposix.rmdir)(space, w_path)
        else:
            path = space.fsencode_w(w_path)
            rposix.unlinkat(path, dir_fd, removedir=True)
    except OSError as e:
        raise wrap_oserror2(space, e, w_path)

@unwrap_spec(errno=c_int)
def strerror(space, errno):
    """Translate an error code to a message string."""
    try:
        return space.wrap(_strerror(errno))
    except ValueError:
        raise OperationError(space.w_ValueError,
                             space.wrap("strerror() argument out of range"))

def getlogin(space):
    """Return the currently logged in user."""
    try:
        cur = os.getlogin()
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.fsdecode(space.wrapbytes(cur))

# ____________________________________________________________

def getstatfields(space):
    # for app_posix.py: export the list of 'st_xxx' names that we know
    # about at RPython level
    return space.newlist([space.wrap(name) for _, (name, _) in STAT_FIELDS])


class State:
    def __init__(self, space):
        self.space = space
        self.w_environ = space.newdict()
        self.random_context = rurandom.init_urandom()

    def startup(self, space):
        space.call_method(self.w_environ, 'clear')
        _convertenviron(space, self.w_environ)

    def _freeze_(self):
        # don't capture the environment in the translated pypy
        self.space.call_method(self.w_environ, 'clear')
        # also reset random_context to a fresh new context (empty so far,
        # to be filled at run-time by rurandom.urandom())
        self.random_context = rurandom.init_urandom()
        return True

def get(space):
    return space.fromcache(State)

if _WIN32:
    def _convertenviron(space, w_env):
        # _wenviron must be initialized in this way if the program is
        # started through main() instead of wmain()
        rwin32._wgetenv(u"")
        for key, value in rwin32._wenviron_items():
            if isinstance(key, str):
                key = key.upper()
            space.setitem(w_env, space.wrap(key), space.wrap(value))

    @unwrap_spec(name=unicode, value=unicode)
    def putenv(space, name, value):
        """Change or add an environment variable."""
        # len includes space for '=' and a trailing NUL
        if len(name) + len(value) + 2 > rwin32._MAX_ENV:
            msg = ("the environment variable is longer than %d characters" %
                   rwin32._MAX_ENV)
            raise OperationError(space.w_ValueError, space.wrap(msg))
        try:
            rwin32._wputenv(name, value)
        except OSError, e:
            raise wrap_oserror(space, e)
else:
    def _convertenviron(space, w_env):
        for key, value in os.environ.items():
            space.setitem(w_env, space.wrapbytes(key), space.wrapbytes(value))

    def putenv(space, w_name, w_value):
        """Change or add an environment variable."""
        try:
            dispatch_filename_2(rposix.putenv)(space, w_name, w_value)
        except OSError, e:
            raise wrap_oserror(space, e)

    def unsetenv(space, w_name):
        """Delete an environment variable."""
        try:
            dispatch_filename(rposix.unsetenv)(space, w_name)
        except KeyError:
            pass
        except OSError, e:
            raise wrap_oserror(space, e)


@unwrap_spec(w_path=WrappedDefault(u"."))
def listdir(space, w_path):
    """listdir(path='.') -> list_of_filenames

Return a list containing the names of the files in the directory.
The list is in arbitrary order.  It does not include the special
entries '.' and '..' even if they are present in the directory.

path can be specified as either str or bytes.  If path is bytes,
  the filenames returned will also be bytes; in all other circumstances
  the filenames returned will be str.
On some platforms, path may also be specified as an open file descriptor;
  the file descriptor must refer to a directory.
  If this functionality is unavailable, using it raises NotImplementedError."""
    if space.isinstance_w(w_path, space.w_bytes):
        dirname = space.str0_w(w_path)
        try:
            result = rposix.listdir(dirname)
        except OSError as e:
            raise wrap_oserror2(space, e, w_path)
        return space.newlist_bytes(result)
    try:
        path = space.fsencode_w(w_path)
    except OperationError as operr:
        if not rposix.HAVE_FDOPENDIR:
            raise oefmt(space.w_TypeError,
                "listdir: illegal type for path argument")
        if not space.isinstance_w(w_path, space.w_int):
            raise oefmt(space.w_TypeError,
                "argument should be string, bytes or integer, not %T", w_path)
        fd = unwrap_fd(space, w_path)
        try:
            result = rposix.fdlistdir(fd)
        except OSError as e:
            raise wrap_oserror2(space, e, w_path)
    else:
        dirname = FileEncoder(space, w_path)
        try:
            result = rposix.listdir(dirname)
        except OSError as e:
            raise wrap_oserror2(space, e, w_path)
    len_result = len(result)
    result_w = [None] * len_result
    for i in range(len_result):
        if _WIN32:
            result_w[i] = space.wrap(result[i])
        else:
            w_bytes = space.wrapbytes(result[i])
            result_w[i] = space.fsdecode(w_bytes)
    return space.newlist(result_w)

def pipe(space):
    "Create a pipe.  Returns (read_end, write_end)."
    try:
        fd1, fd2 = os.pipe()
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.newtuple([space.wrap(fd1), space.wrap(fd2)])

@unwrap_spec(mode=c_int, dir_fd=DirFD(rposix.HAVE_FCHMODAT), follow_symlinks=kwonly(bool))
def chmod(space, w_path, mode, dir_fd=DEFAULT_DIR_FD, follow_symlinks=True):
    """chmod(path, mode, *, dir_fd=None, follow_symlinks=True)

Change the access permissions of a file.

path may always be specified as a string.
On some platforms, path may also be specified as an open file descriptor.
  If this functionality is unavailable, using it raises an exception.
If dir_fd is not None, it should be a file descriptor open to a directory,
  and path should be relative; path will then be relative to that directory.
If follow_symlinks is False, and the last element of the path is a symbolic
  link, chmod will modify the symbolic link itself instead of the file the
  link points to.
It is an error to use dir_fd or follow_symlinks when specifying path as
  an open file descriptor.
dir_fd and follow_symlinks may not be implemented on your platform.
  If they are unavailable, using them will raise a NotImplementedError."""
    if not rposix.HAVE_FCHMODAT:
        if not follow_symlinks:
            raise argument_unavailable(space, "chmod", "follow_symlinks")
        else:
            try:
                dispatch_filename(rposix.chmod)(space, w_path, mode)
                return
            except OSError as e:
                raise wrap_oserror2(space, e, w_path)

    try:
        path = space.fsencode_w(w_path)
    except OperationError as operr:
        if not space.isinstance_w(w_path, space.w_int):
            raise oefmt(space.w_TypeError,
                "argument should be string, bytes or integer, not %T", w_path)
        fd = unwrap_fd(space, w_path)
        _chmod_fd(space, fd, mode)
    else:
        try:
            _chmod_path(path, mode, dir_fd, follow_symlinks)
        except OSError as e:
            if not follow_symlinks and e.errno in (ENOTSUP, EOPNOTSUPP):
                # fchmodat() doesn't actually implement follow_symlinks=False
                # so raise NotImplementedError in this case
                raise argument_unavailable(space, "chmod", "follow_symlinks")
            else:
                raise wrap_oserror2(space, e, w_path)

def _chmod_path(path, mode, dir_fd, follow_symlinks):
    if dir_fd != DEFAULT_DIR_FD or not follow_symlinks:
        rposix.fchmodat(path, mode, dir_fd, follow_symlinks)
    else:
        rposix.chmod(path, mode)

def _chmod_fd(space, fd, mode):
    try:
        os.fchmod(fd, mode)
    except OSError as e:
        raise wrap_oserror(space, e)


@unwrap_spec(fd=c_int, mode=c_int)
def fchmod(space, fd, mode):
    """\
    Change the access permissions of the file given by file descriptor fd.
    """
    _chmod_fd(space, fd, mode)

@unwrap_spec(src_dir_fd=DirFD(rposix.HAVE_RENAMEAT),
        dst_dir_fd=DirFD(rposix.HAVE_RENAMEAT))
def rename(space, w_src, w_dst,
        src_dir_fd=DEFAULT_DIR_FD, dst_dir_fd=DEFAULT_DIR_FD):
    """rename(src, dst, *, src_dir_fd=None, dst_dir_fd=None)

Rename a file or directory.

If either src_dir_fd or dst_dir_fd is not None, it should be a file
  descriptor open to a directory, and the respective path string (src or dst)
  should be relative; the path will then be relative to that directory.
src_dir_fd and dst_dir_fd, may not be implemented on your platform.
  If they are unavailable, using them will raise a NotImplementedError."""
    try:
        if (src_dir_fd != DEFAULT_DIR_FD or dst_dir_fd != DEFAULT_DIR_FD):
            src = space.fsencode_w(w_src)
            dst = space.fsencode_w(w_dst)
            rposix.renameat(src, dst, src_dir_fd, dst_dir_fd)
        else:
            dispatch_filename_2(rposix.rename)(space, w_src, w_dst)
    except OSError, e:
        raise wrap_oserror(space, e)

@unwrap_spec(src_dir_fd=DirFD(rposix.HAVE_RENAMEAT),
        dst_dir_fd=DirFD(rposix.HAVE_RENAMEAT))
def replace(space, w_src, w_dst,
        src_dir_fd=DEFAULT_DIR_FD, dst_dir_fd=DEFAULT_DIR_FD):
    """replace(src, dst, *, src_dir_fd=None, dst_dir_fd=None)

Rename a file or directory, overwriting the destination.

If either src_dir_fd or dst_dir_fd is not None, it should be a file
  descriptor open to a directory, and the respective path string (src or dst)
  should be relative; the path will then be relative to that directory.
src_dir_fd and dst_dir_fd, may not be implemented on your platform.
  If they are unavailable, using them will raise a NotImplementedError."""
    try:
        if (src_dir_fd != DEFAULT_DIR_FD or dst_dir_fd != DEFAULT_DIR_FD):
            src = space.fsencode_w(w_src)
            dst = space.fsencode_w(w_dst)
            rposix.renameat(src, dst, src_dir_fd, dst_dir_fd)
        else:
            dispatch_filename_2(rposix.replace)(space, w_src, w_dst)
    except OSError as e:
        raise wrap_oserror(space, e)

@unwrap_spec(mode=c_int, dir_fd=DirFD(rposix.HAVE_MKFIFOAT))
def mkfifo(space, w_path, mode=0666, dir_fd=DEFAULT_DIR_FD):
    """mkfifo(path, mode=0o666, *, dir_fd=None)

Create a FIFO (a POSIX named pipe).

If dir_fd is not None, it should be a file descriptor open to a directory,
  and path should be relative; path will then be relative to that directory.
dir_fd may not be implemented on your platform.
  If it is unavailable, using it will raise a NotImplementedError."""
    try:
        if dir_fd == DEFAULT_DIR_FD:
            dispatch_filename(rposix.mkfifo)(space, w_path, mode)
        else:
            path = space.fsencode_w(w_path)
            rposix.mkfifoat(path, mode, dir_fd)
    except OSError as e:
        raise wrap_oserror2(space, e, w_path)

@unwrap_spec(mode=c_int, device=c_int, dir_fd=DirFD(rposix.HAVE_MKNODAT))
def mknod(space, w_filename, mode=0600, device=0, dir_fd=DEFAULT_DIR_FD):
    """mknod(filename, mode=0o600, device=0, *, dir_fd=None)

Create a filesystem node (file, device special file or named pipe)
named filename. mode specifies both the permissions to use and the
type of node to be created, being combined (bitwise OR) with one of
S_IFREG, S_IFCHR, S_IFBLK, and S_IFIFO. For S_IFCHR and S_IFBLK,
device defines the newly created device special file (probably using
os.makedev()), otherwise it is ignored.

If dir_fd is not None, it should be a file descriptor open to a directory,
  and path should be relative; path will then be relative to that directory.
dir_fd may not be implemented on your platform.
  If it is unavailable, using it will raise a NotImplementedError."""
    try:
        if dir_fd == DEFAULT_DIR_FD:
            dispatch_filename(rposix.mknod)(space, w_filename, mode, device)
        else:
            fname = space.fsencode_w(w_filename)
            rposix.mknodat(fname, mode, device, dir_fd)
    except OSError as e:
        raise wrap_oserror2(space, e, w_filename)

@unwrap_spec(mask=c_int)
def umask(space, mask):
    "Set the current numeric umask and return the previous umask."
    prevmask = os.umask(mask)
    return space.wrap(prevmask)

def getpid(space):
    "Return the current process id."
    try:
        pid = os.getpid()
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.wrap(pid)

@unwrap_spec(pid=c_int, sig=c_int)
def kill(space, pid, sig):
    "Kill a process with a signal."
    try:
        rposix.kill(pid, sig)
    except OSError, e:
        raise wrap_oserror(space, e)

@unwrap_spec(pgid=c_int, sig=c_int)
def killpg(space, pgid, sig):
    "Kill a process group with a signal."
    try:
        os.killpg(pgid, sig)
    except OSError, e:
        raise wrap_oserror(space, e)

def abort(space):
    """Abort the interpreter immediately.  This 'dumps core' or otherwise fails
in the hardest way possible on the hosting operating system."""
    import signal
    rposix.kill(os.getpid(), signal.SIGABRT)

@unwrap_spec(
    src='fsencode', dst='fsencode',
    src_dir_fd=DirFD(rposix.HAVE_LINKAT), dst_dir_fd=DirFD(rposix.HAVE_LINKAT),
    follow_symlinks=kwonly(bool))
def link(
        space, src, dst,
        src_dir_fd=DEFAULT_DIR_FD, dst_dir_fd=DEFAULT_DIR_FD,
        follow_symlinks=True):
    """\
link(src, dst, *, src_dir_fd=None, dst_dir_fd=None, follow_symlinks=True)

Create a hard link to a file.

If either src_dir_fd or dst_dir_fd is not None, it should be a file
  descriptor open to a directory, and the respective path string (src or dst)
  should be relative; the path will then be relative to that directory.
If follow_symlinks is False, and the last element of src is a symbolic
  link, link will create a link to the symbolic link itself instead of the
  file the link points to.
src_dir_fd, dst_dir_fd, and follow_symlinks may not be implemented on your
  platform.  If they are unavailable, using them will raise a
  NotImplementedError."""
    try:
        if (src_dir_fd != DEFAULT_DIR_FD or dst_dir_fd != DEFAULT_DIR_FD
                or not follow_symlinks):
            rposix.linkat(src, dst, src_dir_fd, dst_dir_fd, follow_symlinks)
        else:
            rposix.link(src, dst)
    except OSError as e:
        raise wrap_oserror(space, e)


@unwrap_spec(dir_fd=DirFD(rposix.HAVE_SYMLINKAT))
def symlink(space, w_src, w_dst, w_target_is_directory=None,
        dir_fd=DEFAULT_DIR_FD):
    """symlink(src, dst, target_is_directory=False, *, dir_fd=None)

Create a symbolic link pointing to src named dst.

target_is_directory is required on Windows if the target is to be
  interpreted as a directory.  (On Windows, symlink requires
  Windows 6.0 or greater, and raises a NotImplementedError otherwise.)
  target_is_directory is ignored on non-Windows platforms.

If dir_fd is not None, it should be a file descriptor open to a directory,
  and path should be relative; path will then be relative to that directory.
dir_fd may not be implemented on your platform.
  If it is unavailable, using it will raise a NotImplementedError."""
    try:
        if dir_fd == DEFAULT_DIR_FD:
            dispatch_filename_2(rposix.symlink)(space, w_src, w_dst)
        else:
            src = space.fsencode_w(w_src)
            dst = space.fsencode_w(w_dst)
            rposix.symlinkat(src, dst, dir_fd)
    except OSError as e:
        raise wrap_oserror(space, e)


@unwrap_spec(dir_fd=DirFD(rposix.HAVE_READLINKAT))
def readlink(space, w_path, dir_fd=DEFAULT_DIR_FD):
    """readlink(path, *, dir_fd=None) -> path

Return a string representing the path to which the symbolic link points.

If dir_fd is not None, it should be a file descriptor open to a directory,
  and path should be relative; path will then be relative to that directory.
dir_fd may not be implemented on your platform.
  If it is unavailable, using it will raise a NotImplementedError."""
    is_unicode = space.isinstance_w(w_path, space.w_unicode)
    if is_unicode:
        path = space.fsencode_w(w_path)
    else:
        path = space.bytes0_w(w_path)
    try:
        if dir_fd == DEFAULT_DIR_FD:
            result = rposix.readlink(path)
        else:
            result = rposix.readlinkat(path, dir_fd)
    except OSError, e:
        raise wrap_oserror2(space, e, w_path)
    w_result = space.wrapbytes(result)
    if is_unicode:
        return space.fsdecode(w_result)
    return w_result

before_fork_hooks = []
after_fork_child_hooks = []
after_fork_parent_hooks = []

@specialize.memo()
def get_fork_hooks(where):
    if where == 'before':
        return before_fork_hooks
    elif where == 'child':
        return after_fork_child_hooks
    elif where == 'parent':
        return after_fork_parent_hooks
    else:
        assert False, "Unknown fork hook"

def add_fork_hook(where, hook):
    "NOT_RPYTHON"
    get_fork_hooks(where).append(hook)

add_fork_hook('child', ExecutionContext._mark_thread_disappeared)

@specialize.arg(0)
def run_fork_hooks(where, space):
    for hook in get_fork_hooks(where):
        hook(space)

def _run_forking_function(space, kind):
    run_fork_hooks('before', space)
    try:
        if kind == "F":
            pid = os.fork()
            master_fd = -1
        elif kind == "P":
            pid, master_fd = os.forkpty()
        else:
            raise AssertionError
    except OSError, e:
        try:
            run_fork_hooks('parent', space)
        except:
            # Don't clobber the OSError if the fork failed
            pass
        raise wrap_oserror(space, e)
    if pid == 0:
        run_fork_hooks('child', space)
    else:
        run_fork_hooks('parent', space)
    return pid, master_fd

def fork(space):
    pid, irrelevant = _run_forking_function(space, "F")
    return space.wrap(pid)

def openpty(space):
    "Open a pseudo-terminal, returning open fd's for both master and slave end."
    try:
        master_fd, slave_fd = os.openpty()
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.newtuple([space.wrap(master_fd), space.wrap(slave_fd)])

def forkpty(space):
    pid, master_fd = _run_forking_function(space, "P")
    return space.newtuple([space.wrap(pid),
                           space.wrap(master_fd)])

@unwrap_spec(pid=c_int, options=c_int)
def waitpid(space, pid, options):
    """ waitpid(pid, options) -> (pid, status)

    Wait for completion of a given child process.
    """
    try:
        pid, status = os.waitpid(pid, options)
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.newtuple([space.wrap(pid), space.wrap(status)])

@unwrap_spec(status=c_int)
def _exit(space, status):
    os._exit(status)

def execv(space, w_path, w_args):
    """ execv(path, args)

Execute an executable path with arguments, replacing current process.

        path: path of executable file
        args: iterable of strings
    """
    command = space.fsencode_w(w_path)
    try:
        args_w = space.unpackiterable(w_args)
        if len(args_w) < 1:
            raise oefmt(space.w_ValueError,
                "execv() arg 2 must not be empty")
        args = [space.fsencode_w(w_arg) for w_arg in args_w]
    except OperationError, e:
        if not e.match(space, space.w_TypeError):
            raise
        raise oefmt(space.w_TypeError,
            "execv() arg 2 must be an iterable of strings")
    try:
        os.execv(command, args)
    except OSError as e:
        raise wrap_oserror(space, e)


def _env2interp(space, w_env):
    env = {}
    w_keys = space.call_method(w_env, 'keys')
    for w_key in space.unpackiterable(w_keys):
        w_value = space.getitem(w_env, w_key)
        env[space.fsencode_w(w_key)] = space.fsencode_w(w_value)
    return env


def execve(space, w_path, w_argv, w_environment):
    """execve(path, args, env)

Execute a path with arguments and environment, replacing current process.

    path: path of executable file
    args: tuple or list of arguments
    env: dictionary of strings mapping to strings

On some platforms, you may specify an open file descriptor for path;
  execve will execute the program the file descriptor is open to.
  If this functionality is unavailable, using it raises NotImplementedError.
    """
    if not (space.isinstance_w(w_argv, space.w_list)
            or space.isinstance_w(w_argv, space.w_tuple)):
        raise oefmt(space.w_TypeError,
            "execve: argv must be a tuple or a list")
    args = [space.fsencode_w(w_arg) for w_arg in space.unpackiterable(w_argv)]
    env = _env2interp(space, w_environment)
    try:
        path = space.fsencode_w(w_path)
    except OperationError:
        if not rposix.HAVE_FEXECVE:
            raise oefmt(space.w_TypeError,
                "execve: illegal type for path argument")
        if not space.isinstance_w(w_path, space.w_int):
            raise oefmt(space.w_TypeError,
                "argument should be string, bytes or integer, not %T", w_path)
        # File descriptor case
        fd = unwrap_fd(space, w_path)
        try:
            rposix.fexecve(fd, args, env)
        except OSError as e:
            raise wrap_oserror(space, e)
    else:
        try:
            os.execve(path, args, env)
        except OSError as e:
            raise wrap_oserror(space, e)

@unwrap_spec(mode=int, path='fsencode')
def spawnv(space, mode, path, w_args):
    args = [space.fsencode_w(w_arg) for w_arg in space.unpackiterable(w_args)]
    try:
        ret = os.spawnv(mode, path, args)
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.wrap(ret)

@unwrap_spec(mode=int, path='fsencode')
def spawnve(space, mode, path, w_args, w_env):
    args = [space.fsencode_w(w_arg) for w_arg in space.unpackiterable(w_args)]
    env = _env2interp(space, w_env)
    try:
        ret = os.spawnve(mode, path, args, env)
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.wrap(ret)


@unwrap_spec(w_times=WrappedDefault(None), w_ns=kwonly(WrappedDefault(None)),
    dir_fd=DirFD(rposix.HAVE_UTIMENSAT), follow_symlinks=kwonly(bool))
def utime(space, w_path, w_times, w_ns, dir_fd=DEFAULT_DIR_FD, follow_symlinks=True):
    """utime(path, times=None, *, ns=None, dir_fd=None, follow_symlinks=True)

Set the access and modified time of path.

path may always be specified as a string.
On some platforms, path may also be specified as an open file descriptor.
  If this functionality is unavailable, using it raises an exception.

If times is not None, it must be a tuple (atime, mtime);
    atime and mtime should be expressed as float seconds since the epoch.
If ns is not None, it must be a tuple (atime_ns, mtime_ns);
    atime_ns and mtime_ns should be expressed as integer nanoseconds
    since the epoch.
If both times and ns are None, utime uses the current time.
Specifying tuples for both times and ns is an error.

If dir_fd is not None, it should be a file descriptor open to a directory,
  and path should be relative; path will then be relative to that directory.
If follow_symlinks is False, and the last element of the path is a symbolic
  link, utime will modify the symbolic link itself instead of the file the
  link points to.
It is an error to use dir_fd or follow_symlinks when specifying path
  as an open file descriptor.
dir_fd and follow_symlinks may not be available on your platform.
  If they are unavailable, using them will raise a NotImplementedError."""
    if (not space.is_w(w_times, space.w_None) and
            not space.is_w(w_ns, space.w_None)):
        raise oefmt(space.w_ValueError,
            "utime: you may specify either 'times' or 'ns' but not both")

    if rposix.HAVE_UTIMENSAT:
        path = space.fsencode_w(w_path)
        try:
            _utimensat(space, path, w_times, w_ns, dir_fd, follow_symlinks)
            return
        except OSError, e:
            raise wrap_oserror2(space, e, w_path)

    if not follow_symlinks:
        raise argument_unavailable(space, "utime", "follow_symlinks")

    if not space.is_w(w_ns, space.w_None):
        raise oefmt(space.w_NotImplementedError,
            "utime: 'ns' unsupported on this platform on PyPy")
    if space.is_w(w_times, space.w_None):
        try:
            dispatch_filename(rposix.utime, 1)(space, w_path, None)
            return
        except OSError, e:
            raise wrap_oserror2(space, e, w_path)
    try:
        msg = "utime() arg 2 must be a tuple (atime, mtime) or None"
        args_w = space.fixedview(w_times)
        if len(args_w) != 2:
            raise OperationError(space.w_TypeError, space.wrap(msg))
        actime = space.float_w(args_w[0], allow_conversion=False)
        modtime = space.float_w(args_w[1], allow_conversion=False)
        dispatch_filename(rposix.utime, 2)(space, w_path, (actime, modtime))
    except OSError, e:
        raise wrap_oserror2(space, e, w_path)
    except OperationError, e:
        if not e.match(space, space.w_TypeError):
            raise
        raise OperationError(space.w_TypeError, space.wrap(msg))


def _utimensat(space, path, w_times, w_ns, dir_fd, follow_symlinks):
    if space.is_w(w_times, space.w_None) and space.is_w(w_ns, space.w_None):
        atime_s = mtime_s = 0
        atime_ns = mtime_ns = rposix.UTIME_NOW
    elif not space.is_w(w_times, space.w_None):
        times_w = space.fixedview(w_times)
        if len(times_w) != 2:
            raise oefmt(space.w_TypeError,
                "utime: 'times' must be either a tuple of two ints or None")
        atime_s, atime_ns = convert_seconds(space, times_w[0])
        mtime_s, mtime_ns = convert_seconds(space, times_w[1])
    else:
        args_w = space.fixedview(w_ns)
        if len(args_w) != 2:
            raise oefmt(space.w_TypeError,
                "utime: 'ns' must be a tuple of two ints")
        atime_s, atime_ns = convert_ns(space, args_w[0])
        mtime_s, mtime_ns = convert_ns(space, args_w[1])

    rposix.utimensat(
        path, atime_s, atime_ns, mtime_s, mtime_ns,
        dir_fd=dir_fd, follow_symlinks=follow_symlinks)

def convert_seconds(space, w_time):
    if space.isinstance_w(w_time, space.w_float):
        time = space.float_w(w_time)
        fracpart, intpart = modf(time)
        if fracpart < 0:
            fracpart += 1.
            intpart -= 1.
        return int(intpart), int(fracpart*1e9)
    else:
        time = space.int_w(w_time)
        return time, 0

def convert_ns(space, w_ns_time):
    w_billion = space.wrap(1000000000)
    w_res = space.divmod(w_ns_time, w_billion)
    res_w = space.fixedview(w_res)
    time_int = space.int_w(res_w[0])
    time_frac = space.int_w(res_w[1])
    return time_int, time_frac


def uname(space):
    """ uname() -> (sysname, nodename, release, version, machine)

    Return a tuple identifying the current operating system.
    """
    try:
        r = os.uname()
    except OSError, e:
        raise wrap_oserror(space, e)
    l_w = [space.fsdecode(space.wrapbytes(i))
           for i in [r[0], r[1], r[2], r[3], r[4]]]
    w_tuple = space.newtuple(l_w)
    w_uname_result = space.getattr(space.getbuiltinmodule(os.name),
                                   space.wrap('uname_result'))
    return space.call_function(w_uname_result, w_tuple)

def getuid(space):
    """ getuid() -> uid

    Return the current process's user id.
    """
    return space.wrap(os.getuid())

@unwrap_spec(arg=c_uid_t)
def setuid(space, arg):
    """ setuid(uid)

    Set the current process's user id.
    """
    check_uid_range(space, arg)
    try:
        os.setuid(arg)
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.w_None

@unwrap_spec(arg=c_uid_t)
def seteuid(space, arg):
    """ seteuid(uid)

    Set the current process's effective user id.
    """
    check_uid_range(space, arg)
    try:
        os.seteuid(arg)
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.w_None

@unwrap_spec(arg=c_gid_t)
def setgid(space, arg):
    """ setgid(gid)

    Set the current process's group id.
    """
    check_uid_range(space, arg)
    try:
        os.setgid(arg)
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.w_None

@unwrap_spec(arg=c_gid_t)
def setegid(space, arg):
    """ setegid(gid)

    Set the current process's effective group id.
    """
    check_uid_range(space, arg)
    try:
        os.setegid(arg)
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.w_None

@unwrap_spec(path='fsencode')
def chroot(space, path):
    """ chroot(path)

    Change root directory to path.
    """
    try:
        os.chroot(path)
    except OSError, e:
        raise wrap_oserror(space, e, path)
    return space.w_None

def getgid(space):
    """ getgid() -> gid

    Return the current process's group id.
    """
    return space.wrap(os.getgid())

def getegid(space):
    """ getegid() -> gid

    Return the current process's effective group id.
    """
    return space.wrap(os.getegid())

def geteuid(space):
    """ geteuid() -> euid

    Return the current process's effective user id.
    """
    return space.wrap(os.geteuid())

def getgroups(space):
    """ getgroups() -> list of group IDs

    Return list of supplemental group IDs for the process.
    """
    try:
        list = os.getgroups()
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.newlist([space.wrap(e) for e in list])

def setgroups(space, w_list):
    """ setgroups(list)

    Set the groups of the current process to list.
    """
    list = []
    for w_gid in space.unpackiterable(w_list):
        gid = space.int_w(w_gid)
        check_uid_range(space, gid)
        list.append(gid)
    try:
        os.setgroups(list[:])
    except OSError, e:
        raise wrap_oserror(space, e)

@unwrap_spec(username=str, gid=c_gid_t)
def initgroups(space, username, gid):
    """ initgroups(username, gid) -> None

    Call the system initgroups() to initialize the group access list with all of
    the groups of which the specified username is a member, plus the specified
    group id.
    """
    try:
        os.initgroups(username, gid)
    except OSError, e:
        raise wrap_oserror(space, e)

def getpgrp(space):
    """ getpgrp() -> pgrp

    Return the current process group id.
    """
    return space.wrap(os.getpgrp())

def setpgrp(space):
    """ setpgrp()

    Make this process a session leader.
    """
    try:
        os.setpgrp()
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.w_None

def getppid(space):
    """ getppid() -> ppid

    Return the parent's process id.
    """
    return space.wrap(os.getppid())

@unwrap_spec(pid=c_int)
def getpgid(space, pid):
    """ getpgid(pid) -> pgid

    Call the system call getpgid().
    """
    try:
        pgid = os.getpgid(pid)
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.wrap(pgid)

@unwrap_spec(pid=c_int, pgrp=c_int)
def setpgid(space, pid, pgrp):
    """ setpgid(pid, pgrp)

    Call the system call setpgid().
    """
    try:
        os.setpgid(pid, pgrp)
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.w_None

@unwrap_spec(ruid=c_uid_t, euid=c_uid_t)
def setreuid(space, ruid, euid):
    """ setreuid(ruid, euid)

    Set the current process's real and effective user ids.
    """
    check_uid_range(space, ruid)
    check_uid_range(space, euid)
    try:
        os.setreuid(ruid, euid)
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.w_None

@unwrap_spec(rgid=c_gid_t, egid=c_gid_t)
def setregid(space, rgid, egid):
    """ setregid(rgid, egid)

    Set the current process's real and effective group ids.
    """
    check_uid_range(space, rgid)
    check_uid_range(space, egid)
    try:
        os.setregid(rgid, egid)
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.w_None

@unwrap_spec(pid=c_int)
def getsid(space, pid):
    """ getsid(pid) -> sid

    Call the system call getsid().
    """
    try:
        sid = os.getsid(pid)
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.wrap(sid)

def setsid(space):
    """ setsid()

    Call the system call setsid().
    """
    try:
        os.setsid()
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.w_None

@unwrap_spec(fd=c_int)
def tcgetpgrp(space, fd):
    """ tcgetpgrp(fd) -> pgid

    Return the process group associated with the terminal given by a fd.
    """
    try:
        pgid = os.tcgetpgrp(fd)
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.wrap(pgid)

@unwrap_spec(fd=c_int, pgid=c_gid_t)
def tcsetpgrp(space, fd, pgid):
    """ tcsetpgrp(fd, pgid)

    Set the process group associated with the terminal given by a fd.
    """
    try:
        os.tcsetpgrp(fd, pgid)
    except OSError, e:
        raise wrap_oserror(space, e)

def getresuid(space):
    """ getresuid() -> (ruid, euid, suid)

    Get tuple of the current process's real, effective, and saved user ids.
    """
    try:
        (ruid, euid, suid) = os.getresuid()
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.newtuple([space.wrap(ruid),
                           space.wrap(euid),
                           space.wrap(suid)])

def getresgid(space):
    """ getresgid() -> (rgid, egid, sgid)

    Get tuple of the current process's real, effective, and saved group ids.
    """
    try:
        (rgid, egid, sgid) = os.getresgid()
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.newtuple([space.wrap(rgid),
                           space.wrap(egid),
                           space.wrap(sgid)])

@unwrap_spec(ruid=c_uid_t, euid=c_uid_t, suid=c_uid_t)
def setresuid(space, ruid, euid, suid):
    """ setresuid(ruid, euid, suid)

    Set the current process's real, effective, and saved user ids.
    """
    try:
        os.setresuid(ruid, euid, suid)
    except OSError, e:
        raise wrap_oserror(space, e)

@unwrap_spec(rgid=c_gid_t, egid=c_gid_t, sgid=c_gid_t)
def setresgid(space, rgid, egid, sgid):
    """ setresgid(rgid, egid, sgid)

    Set the current process's real, effective, and saved group ids.
    """
    try:
        os.setresgid(rgid, egid, sgid)
    except OSError, e:
        raise wrap_oserror(space, e)

def declare_new_w_star(name):
    if name in ('WEXITSTATUS', 'WSTOPSIG', 'WTERMSIG'):
        @unwrap_spec(status=c_int)
        def WSTAR(space, status):
            return space.wrap(getattr(os, name)(status))
    else:
        @unwrap_spec(status=c_int)
        def WSTAR(space, status):
            return space.newbool(getattr(os, name)(status))
    WSTAR.__doc__ = getattr(os, name).__doc__
    WSTAR.func_name = name
    return WSTAR

for name in rposix.WAIT_MACROS:
    if hasattr(os, name):
        func = declare_new_w_star(name)
        globals()[name] = func


@unwrap_spec(fd=c_int)
def ttyname(space, fd):
    try:
        return space.fsdecode(space.wrapbytes(os.ttyname(fd)))
    except OSError, e:
        raise wrap_oserror(space, e)


def confname_w(space, w_name, namespace):
    # XXX slightly non-nice, reuses the sysconf of the underlying os module
    if space.isinstance_w(w_name, space.w_unicode):
        try:
            num = namespace[space.str_w(w_name)]
        except KeyError:
            raise OperationError(space.w_ValueError,
                                 space.wrap("unrecognized configuration name"))
    else:
        num = space.int_w(w_name)
    return num

def sysconf(space, w_name):
    num = confname_w(space, w_name, os.sysconf_names)
    try:
        res = os.sysconf(num)
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.wrap(res)

@unwrap_spec(fd=c_int)
def fpathconf(space, fd, w_name):
    num = confname_w(space, w_name, os.pathconf_names)
    try:
        res = os.fpathconf(fd, num)
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.wrap(res)

@unwrap_spec(path='str0')
def pathconf(space, path, w_name):
    num = confname_w(space, w_name, os.pathconf_names)
    try:
        res = os.pathconf(path, num)
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.wrap(res)

def confstr(space, w_name):
    num = confname_w(space, w_name, os.confstr_names)
    try:
        res = os.confstr(num)
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.wrap(res)

@unwrap_spec(
    uid=c_uid_t, gid=c_gid_t,
    dir_fd=DirFD(rposix.HAVE_FCHOWNAT), follow_symlinks=kwonly(bool))
def chown(space, w_path, uid, gid, dir_fd=DEFAULT_DIR_FD, follow_symlinks=True):
    """chown(path, uid, gid, *, dir_fd=None, follow_symlinks=True)

Change the owner and group id of path to the numeric uid and gid.

path may always be specified as a string.
On some platforms, path may also be specified as an open file descriptor.
  If this functionality is unavailable, using it raises an exception.
If dir_fd is not None, it should be a file descriptor open to a directory,
  and path should be relative; path will then be relative to that directory.
If follow_symlinks is False, and the last element of the path is a symbolic
  link, chown will modify the symbolic link itself instead of the file the
  link points to.
It is an error to use dir_fd or follow_symlinks when specifying path as
  an open file descriptor.
dir_fd and follow_symlinks may not be implemented on your platform.
  If they are unavailable, using them will raise a NotImplementedError."""
    check_uid_range(space, uid)
    check_uid_range(space, gid)
    if not (rposix.HAVE_LCHOWN or rposix.HAVE_FCHMODAT):
        if not follow_symlinks:
            raise argument_unavailable(space, 'chown', 'follow_symlinks')
    try:
        path = space.fsencode_w(w_path)
    except OperationError:
        if not space.isinstance_w(w_path, space.w_int):
            raise oefmt(space.w_TypeError,
                "argument should be string, bytes or integer, not %T", w_path)
        # File descriptor case
        fd = unwrap_fd(space, w_path)
        if dir_fd != DEFAULT_DIR_FD:
            raise oefmt(space.w_ValueError,
                "chown: can't specify both dir_fd and fd")
        if not follow_symlinks:
            raise oefmt(space.w_ValueError,
                "chown: cannnot use fd and follow_symlinks together")
        try:
            os.fchown(fd, uid, gid)
        except OSError as e:
            raise wrap_oserror(space, e)
    else:
        # String case
        try:
            if (rposix.HAVE_LCHOWN and
                    dir_fd == DEFAULT_DIR_FD and not follow_symlinks):
                os.lchown(path, uid, gid)
            elif rposix.HAVE_FCHOWNAT and (
                    not follow_symlinks or dir_fd != DEFAULT_DIR_FD):
                rposix.fchownat(path, uid, gid, dir_fd, follow_symlinks)
            else:
                assert follow_symlinks
                assert dir_fd == DEFAULT_DIR_FD
                os.chown(path, uid, gid)
        except OSError as e:
            raise wrap_oserror2(space, e, w_path)


@unwrap_spec(path='fsencode', uid=c_uid_t, gid=c_gid_t)
def lchown(space, path, uid, gid):
    """lchown(path, uid, gid)

Change the owner and group id of path to the numeric uid and gid.
This function will not follow symbolic links.
Equivalent to os.chown(path, uid, gid, follow_symlinks=False)."""
    check_uid_range(space, uid)
    check_uid_range(space, gid)
    try:
        os.lchown(path, uid, gid)
    except OSError, e:
        raise wrap_oserror(space, e, path)

@unwrap_spec(uid=c_uid_t, gid=c_gid_t)
def fchown(space, w_fd, uid, gid):
    """fchown(fd, uid, gid)

Change the owner and group id of the file given by file descriptor
fd to the numeric uid and gid.  Equivalent to os.chown(fd, uid, gid)."""
    fd = space.c_filedescriptor_w(w_fd)
    check_uid_range(space, uid)
    check_uid_range(space, gid)
    try:
        os.fchown(fd, uid, gid)
    except OSError, e:
        raise wrap_oserror(space, e)

def getloadavg(space):
    try:
        load = os.getloadavg()
    except OSError:
        raise OperationError(space.w_OSError,
                             space.wrap("Load averages are unobtainable"))
    return space.newtuple([space.wrap(load[0]),
                           space.wrap(load[1]),
                           space.wrap(load[2])])

@unwrap_spec(major=c_int, minor=c_int)
def makedev(space, major, minor):
    result = os.makedev(major, minor)
    return space.wrap(result)

@unwrap_spec(device="c_uint")
def major(space, device):
    result = os.major(intmask(device))
    return space.wrap(result)

@unwrap_spec(device="c_uint")
def minor(space, device):
    result = os.minor(intmask(device))
    return space.wrap(result)

@unwrap_spec(inc=c_int)
def nice(space, inc):
    "Decrease the priority of process by inc and return the new priority."
    try:
        res = os.nice(inc)
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.wrap(res)

@unwrap_spec(n=int)
def urandom(space, n):
    """urandom(n) -> str

    Return a string of n random bytes suitable for cryptographic use.
    """
    context = get(space).random_context
    try:
        return space.wrapbytes(rurandom.urandom(context, n))
    except OSError, e:
        raise wrap_oserror(space, e)

def ctermid(space):
    """ctermid() -> string

    Return the name of the controlling terminal for this process.
    """
    return space.fsdecode(space.wrapbytes(os.ctermid()))

@unwrap_spec(fd=c_int)
def device_encoding(space, fd):
    """device_encoding(fd) -> str

    Return a string describing the encoding of the device if the output
    is a terminal; else return None.
    """
    if not (rposix.is_valid_fd(fd) and os.isatty(fd)):
        return space.w_None
    if _WIN32:
        if fd == 0:
            return space.wrap('cp%d' % rwin32.GetConsoleCP())
        if fd in (1, 2):
            return space.wrap('cp%d' % rwin32.GetConsoleOutputCP())
    from rpython.rlib import rlocale
    if rlocale.HAVE_LANGINFO:
        codeset = rlocale.nl_langinfo(rlocale.CODESET)
        if codeset:
            return space.wrap(codeset)
    return space.w_None

if _WIN32:
    from pypy.module.posix import interp_nt as nt

    @unwrap_spec(fd=c_int)
    def _getfileinformation(space, fd):
        try:
            info = nt._getfileinformation(fd)
        except OSError as e:
            raise wrap_oserror(space, e)
        return space.newtuple([space.wrap(info[0]),
                               space.wrap(info[1]),
                               space.wrap(info[2])])

    def _getfinalpathname(space, w_path):
        path = space.unicode_w(w_path)
        try:
            result = nt._getfinalpathname(path)
        except nt.LLNotImplemented as e:
            raise OperationError(space.w_NotImplementedError,
                                 space.wrap(e.msg))
        except OSError as e:
            raise wrap_oserror2(space, e, w_path)
        return space.wrap(result)


def chflags():
    """chflags(path, flags, *, follow_symlinks=True)

Set file flags.

If follow_symlinks is False, and the last element of the path is a symbolic
  link, chflags will change flags on the symbolic link itself instead of the
  file the link points to.
follow_symlinks may not be implemented on your platform.  If it is
unavailable, using it will raise a NotImplementedError."""

def lchflags():
    """lchflags(path, flags)

Set file flags.
This function will not follow symbolic links.
Equivalent to chflags(path, flags, follow_symlinks=False)."""

def getxattr():
    """getxattr(path, attribute, *, follow_symlinks=True) -> value

Return the value of extended attribute attribute on path.

path may be either a string or an open file descriptor.
If follow_symlinks is False, and the last element of the path is a symbolic
  link, getxattr will examine the symbolic link itself instead of the file
  the link points to."""

def setxattr():
    """setxattr(path, attribute, value, flags=0, *, follow_symlinks=True)

Set extended attribute attribute on path to value.
path may be either a string or an open file descriptor.
If follow_symlinks is False, and the last element of the path is a symbolic
  link, setxattr will modify the symbolic link itself instead of the file
  the link points to."""


def removexattr():
    """removexattr(path, attribute, *, follow_symlinks=True)

Remove extended attribute attribute on path.
path may be either a string or an open file descriptor.
If follow_symlinks is False, and the last element of the path is a symbolic
  link, removexattr will modify the symbolic link itself instead of the file
  the link points to."""

def listxattr():
    """listxattr(path='.', *, follow_symlinks=True)

Return a list of extended attributes on path.

path may be either None, a string, or an open file descriptor.
if path is None, listxattr will examine the current directory.
If follow_symlinks is False, and the last element of the path is a symbolic
  link, listxattr will examine the symbolic link itself instead of the file
  the link points to."""


have_functions = []
for name in """FCHDIR FCHMOD FCHMODAT FCHOWN FCHOWNAT FEXECVE FDOPENDIR
               FPATHCONF FSTATAT FSTATVFS FTRUNCATE FUTIMENS FUTIMES
               FUTIMESAT LINKAT LCHFLAGS LCHMOD LCHOWN LSTAT LUTIMES
               MKDIRAT MKFIFOAT MKNODAT OPENAT READLINKAT RENAMEAT
               SYMLINKAT UNLINKAT UTIMENSAT""".split():
    if getattr(rposix, "HAVE_%s" % name):
        have_functions.append("HAVE_%s" % name)
if _WIN32:
    have_functions.append("HAVE_MS_WINDOWS")
