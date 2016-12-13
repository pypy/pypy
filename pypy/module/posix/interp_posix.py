import os
import sys

from rpython.rlib import rposix, rposix_stat
from rpython.rlib import objectmodel, rurandom
from rpython.rlib.objectmodel import specialize
from rpython.rlib.rarithmetic import r_longlong, intmask, r_uint
from rpython.rlib.unroll import unrolling_iterable

from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.error import (
    OperationError, oefmt, wrap_oserror, wrap_oserror2)
from pypy.interpreter.executioncontext import ExecutionContext
from pypy.module.sys.interp_encoding import getfilesystemencoding


_WIN32 = sys.platform == 'win32'
if _WIN32:
    from rpython.rlib.rwin32 import _MAX_ENV

c_int = "c_int"

# CPython 2.7 semantics used to be too messy, differing on 32-bit vs
# 64-bit, but this was cleaned up in recent 2.7.x.  Now, any function
# taking a uid_t or gid_t accepts numbers in range(-1, 2**32) as an
# r_uint, with -1 being equivalent to 2**32-1.  Any function that
# returns a uid_t or gid_t returns either an int or a long, depending
# on whether it fits or not, but always positive.
c_uid_t = 'c_uid_t'
c_gid_t = 'c_uid_t'

def wrap_uid(space, uid):
    if uid <= r_uint(sys.maxint):
        return space.wrap(intmask(uid))
    else:
        return space.wrap(uid)     # an unsigned number
wrap_gid = wrap_uid

def fsencode_w(space, w_obj):
    if space.isinstance_w(w_obj, space.w_unicode):
        w_obj = space.call_method(w_obj, 'encode',
                                  getfilesystemencoding(space))
    return space.str0_w(w_obj)

class FileEncoder(object):
    is_unicode = True

    def __init__(self, space, w_obj):
        self.space = space
        self.w_obj = w_obj

    def as_bytes(self):
        return fsencode_w(self.space, self.w_obj)

    def as_unicode(self):
        return self.space.unicode0_w(self.w_obj)

class FileDecoder(object):
    is_unicode = False

    def __init__(self, space, w_obj):
        self.space = space
        self.w_obj = w_obj

    def as_bytes(self):
        return self.space.str0_w(self.w_obj)

    def as_unicode(self):
        space = self.space
        w_unicode = space.call_method(self.w_obj, 'decode',
                                      getfilesystemencoding(space))
        return space.unicode0_w(w_unicode)

@specialize.memo()
def dispatch_filename(func, tag=0):
    def dispatch(space, w_fname, *args):
        if space.isinstance_w(w_fname, space.w_unicode):
            fname = FileEncoder(space, w_fname)
            return func(fname, *args)
        else:
            fname = space.str0_w(w_fname)
            return func(fname, *args)
    return dispatch

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

@unwrap_spec(flag=c_int, mode=c_int)
def open(space, w_fname, flag, mode=0777):
    """Open a file (for low level IO).
Return a file descriptor (a small integer)."""
    try:
        fd = dispatch_filename(rposix.open)(
            space, w_fname, flag, mode)
    except OSError as e:
        raise wrap_oserror2(space, e, w_fname)
    return space.wrap(fd)

@unwrap_spec(fd=c_int, pos=r_longlong, how=c_int)
def lseek(space, fd, pos, how):
    """Set the current position of a file descriptor.  Return the new position.
If how == 0, 'pos' is relative to the start of the file; if how == 1, to the
current position; if how == 2, to the end."""
    try:
        pos = os.lseek(fd, pos, how)
    except OSError as e:
        raise wrap_oserror(space, e)
    else:
        return space.wrap(pos)

@unwrap_spec(fd=c_int)
def isatty(space, fd):
    """Return True if 'fd' is an open file descriptor connected to the
slave end of a terminal."""
    try:
        res = os.isatty(fd)
    except OSError as e:
        raise wrap_oserror(space, e)
    else:
        return space.wrap(res)

@unwrap_spec(fd=c_int, buffersize=int)
def read(space, fd, buffersize):
    """Read data from a file descriptor."""
    try:
        s = os.read(fd, buffersize)
    except OSError as e:
        raise wrap_oserror(space, e)
    else:
        return space.wrap(s)

@unwrap_spec(fd=c_int)
def write(space, fd, w_data):
    """Write a string to a file descriptor.  Return the number of bytes
actually written, which may be smaller than len(data)."""
    data = space.getarg_w('s*', w_data)
    try:
        res = os.write(fd, data.as_str())
    except OSError as e:
        raise wrap_oserror(space, e)
    else:
        return space.wrap(res)

@unwrap_spec(fd=c_int)
def close(space, fd):
    """Close a file descriptor (for low level IO)."""
    try:
        os.close(fd)
    except OSError as e:
        raise wrap_oserror(space, e)

@unwrap_spec(fd_low=c_int, fd_high=c_int)
def closerange(fd_low, fd_high):
    """Closes all file descriptors in [fd_low, fd_high), ignoring errors."""
    rposix.closerange(fd_low, fd_high)

@unwrap_spec(fd=c_int, length=r_longlong)
def ftruncate(space, fd, length):
    """Truncate a file to a specified length."""
    try:
        os.ftruncate(fd, length)
    except IOError as e:
        if not objectmodel.we_are_translated():
            # Python 2.6 raises an IOError here. Let's not repeat that mistake.
            w_error = space.call_function(space.w_OSError, space.wrap(e.errno),
                                          space.wrap(e.strerror),
                                          space.wrap(e.filename))
            raise OperationError(space.w_OSError, w_error)
        raise AssertionError
    except OSError as e:
        raise wrap_oserror(space, e)

def fsync(space, w_fd):
    """Force write of file with filedescriptor to disk."""
    fd = space.c_filedescriptor_w(w_fd)
    try:
        os.fsync(fd)
    except OSError as e:
        raise wrap_oserror(space, e)

def fdatasync(space, w_fd):
    """Force write of file with filedescriptor to disk.
Does not force update of metadata."""
    fd = space.c_filedescriptor_w(w_fd)
    try:
        os.fdatasync(fd)
    except OSError as e:
        raise wrap_oserror(space, e)

def fchdir(space, w_fd):
    """Change to the directory of the given file descriptor.  fildes must be
opened on a directory, not a file."""
    fd = space.c_filedescriptor_w(w_fd)
    try:
        os.fchdir(fd)
    except OSError as e:
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
        if i < rposix_stat.N_INDEXABLE_FIELDS:
            # get the first 10 items by indexing; this gives us
            # 'st_Xtime' as an integer, too
            w_value = space.wrap(st[i])
            lst[i] = w_value
        elif name.startswith('st_'):    # exclude 'nsec_Xtime'
            w_value = space.wrap(getattr(st, name))
            space.setitem(w_keywords, space.wrap(name), w_value)

    # non-rounded values for name-based access
    if stat_float_times:
        space.setitem(w_keywords,
                      space.wrap('st_atime'), space.wrap(st.st_atime))
        space.setitem(w_keywords,
                      space.wrap('st_mtime'), space.wrap(st.st_mtime))
        space.setitem(w_keywords,
                      space.wrap('st_ctime'), space.wrap(st.st_ctime))
    #else:
    #   filled by the __init__ method

    w_tuple = space.newtuple(lst)
    w_stat_result = space.getattr(space.getbuiltinmodule(os.name),
                                  space.wrap('stat_result'))
    return space.call_function(w_stat_result, w_tuple, w_keywords)


def build_statvfs_result(space, st):
    vals_w = [None] * len(rposix_stat.STATVFS_FIELDS)
    for i, (name, _) in STATVFS_FIELDS:
        vals_w[i] = space.wrap(getattr(st, name))
    w_tuple = space.newtuple(vals_w)
    w_statvfs_result = space.getattr(space.getbuiltinmodule(os.name), space.wrap('statvfs_result'))
    return space.call_function(w_statvfs_result, w_tuple)


@unwrap_spec(fd=c_int)
def fstat(space, fd):
    """Perform a stat system call on the file referenced to by an open
file descriptor."""
    try:
        st = rposix_stat.fstat(fd)
    except OSError as e:
        raise wrap_oserror(space, e)
    else:
        return build_stat_result(space, st)

def stat(space, w_path):
    """Perform a stat system call on the given path.  Return an object
with (at least) the following attributes:
    st_mode
    st_ino
    st_dev
    st_nlink
    st_uid
    st_gid
    st_size
    st_atime
    st_mtime
    st_ctime
"""

    try:
        st = dispatch_filename(rposix_stat.stat)(space, w_path)
    except OSError as e:
        raise wrap_oserror2(space, e, w_path)
    else:
        return build_stat_result(space, st)

def lstat(space, w_path):
    "Like stat(path), but do not follow symbolic links."
    try:
        st = dispatch_filename(rposix_stat.lstat)(space, w_path)
    except OSError as e:
        raise wrap_oserror2(space, e, w_path)
    else:
        return build_stat_result(space, st)

class StatState(object):
    def __init__(self, space):
        self.stat_float_times = True

@unwrap_spec(newval=int)
def stat_float_times(space, newval=-1):
    """stat_float_times([newval]) -> oldval

Determine whether os.[lf]stat represents time stamps as float objects.
If newval is True, future calls to stat() return floats, if it is False,
future calls return ints.
If newval is omitted, return the current setting.
"""
    state = space.fromcache(StatState)

    if newval == -1:
        return space.wrap(state.stat_float_times)
    else:
        state.stat_float_times = (newval != 0)


@unwrap_spec(fd=c_int)
def fstatvfs(space, fd):
    try:
        st = rposix_stat.fstatvfs(fd)
    except OSError as e:
        raise wrap_oserror(space, e)
    else:
        return build_statvfs_result(space, st)


def statvfs(space, w_path):
    try:
        st = dispatch_filename(rposix_stat.statvfs)(space, w_path)
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
    except OSError as e:
        raise wrap_oserror(space, e)
    else:
        return space.wrap(newfd)

@unwrap_spec(old_fd=c_int, new_fd=c_int)
def dup2(space, old_fd, new_fd):
    """Duplicate a file descriptor."""
    try:
        os.dup2(old_fd, new_fd)
    except OSError as e:
        raise wrap_oserror(space, e)

@unwrap_spec(mode=c_int)
def access(space, w_path, mode):
    """
    access(path, mode) -> 1 if granted, 0 otherwise

    Use the real uid/gid to test for access to a path.  Note that most
    operations will use the effective uid/gid, therefore this routine can
    be used in a suid/sgid environment to test if the invoking user has the
    specified access to the path.  The mode argument can be F_OK to test
    existence, or the inclusive-OR of R_OK, W_OK, and X_OK.
    """
    try:
        ok = dispatch_filename(rposix.access)(space, w_path, mode)
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
    except OSError as e:
        raise wrap_oserror(space, e)
    else:
        return space.newtuple([space.wrap(times[0]),
                               space.wrap(times[1]),
                               space.wrap(times[2]),
                               space.wrap(times[3]),
                               space.wrap(times[4])])

@unwrap_spec(cmd='str0')
def system(space, cmd):
    """Execute the command (a string) in a subshell."""
    try:
        rc = os.system(cmd)
    except OSError as e:
        raise wrap_oserror(space, e)
    else:
        return space.wrap(rc)

def unlink(space, w_path):
    """Remove a file (same as remove(path))."""
    try:
        dispatch_filename(rposix.unlink)(space, w_path)
    except OSError as e:
        raise wrap_oserror2(space, e, w_path)

def remove(space, w_path):
    """Remove a file (same as unlink(path))."""
    try:
        dispatch_filename(rposix.unlink)(space, w_path)
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
            w_fullpath = space.wrap(fullpath)
    except OSError as e:
        raise wrap_oserror2(space, e, w_path)
    else:
        return w_fullpath

def getcwd(space):
    """Return the current working directory."""
    try:
        cur = os.getcwd()
    except OSError as e:
        raise wrap_oserror(space, e)
    else:
        return space.wrap(cur)

if _WIN32:
    def getcwdu(space):
        """Return the current working directory as a unicode string."""
        try:
            cur = os.getcwdu()
        except OSError as e:
            raise wrap_oserror(space, e)
        else:
            return space.wrap(cur)
else:
    def getcwdu(space):
        """Return the current working directory as a unicode string."""
        w_filesystemencoding = getfilesystemencoding(space)
        return space.call_method(getcwd(space), 'decode',
                                 w_filesystemencoding)

def chdir(space, w_path):
    """Change the current working directory to the specified path."""
    try:
        dispatch_filename(rposix.chdir)(space, w_path)
    except OSError as e:
        raise wrap_oserror2(space, e, w_path)

@unwrap_spec(mode=c_int)
def mkdir(space, w_path, mode=0777):
    """Create a directory."""
    try:
        dispatch_filename(rposix.mkdir)(space, w_path, mode)
    except OSError as e:
        raise wrap_oserror2(space, e, w_path)

def rmdir(space, w_path):
    """Remove a directory."""
    try:
        dispatch_filename(rposix.rmdir)(space, w_path)
    except OSError as e:
        raise wrap_oserror2(space, e, w_path)

@unwrap_spec(errno=c_int)
def strerror(space, errno):
    """Translate an error code to a message string."""
    try:
        text = os.strerror(errno)
    except ValueError:
        raise oefmt(space.w_ValueError, "strerror() argument out of range")
    return space.wrap(text)

def getlogin(space):
    """Return the currently logged in user."""
    try:
        cur = os.getlogin()
    except OSError as e:
        raise wrap_oserror(space, e)
    else:
        return space.wrap(cur)

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

def _convertenviron(space, w_env):
    space.call_method(w_env, 'clear')
    for key, value in os.environ.items():
        space.setitem(w_env, space.wrap(key), space.wrap(value))

@unwrap_spec(name='str0', value='str0')
def putenv(space, name, value):
    """Change or add an environment variable."""
    if _WIN32 and len(name) > _MAX_ENV:
        raise oefmt(space.w_ValueError,
                    "the environment variable is longer than %d bytes",
                    _MAX_ENV)
    if _WIN32 and not objectmodel.we_are_translated() and value == '':
        # special case: on Windows, _putenv("NAME=") really means that
        # we want to delete NAME.  So that's what the os.environ[name]=''
        # below will do after translation.  But before translation, it
        # will cache the environment value '' instead of <missing> and
        # then return that.  We need to avoid that.
        del os.environ[name]
        return
    try:
        os.environ[name] = value
    except OSError as e:
        raise wrap_oserror(space, e)

@unwrap_spec(name='str0')
def unsetenv(space, name):
    """Delete an environment variable."""
    try:
        del os.environ[name]
    except KeyError:
        pass
    except OSError as e:
        raise wrap_oserror(space, e)


def listdir(space, w_dirname):
    """Return a list containing the names of the entries in the directory.

\tpath: path of directory to list

The list is in arbitrary order.  It does not include the special
entries '.' and '..' even if they are present in the directory."""
    try:
        if space.isinstance_w(w_dirname, space.w_unicode):
            dirname = FileEncoder(space, w_dirname)
            result = rposix.listdir(dirname)
            w_fs_encoding = getfilesystemencoding(space)
            len_result = len(result)
            result_w = [None] * len_result
            for i in range(len_result):
                w_bytes = space.wrap(result[i])
                try:
                    result_w[i] = space.call_method(w_bytes,
                                                    "decode", w_fs_encoding)
                except OperationError as e:
                    # fall back to the original byte string
                    if e.async(space):
                        raise
                    result_w[i] = w_bytes
            return space.newlist(result_w)
        else:
            dirname = space.str0_w(w_dirname)
            result = rposix.listdir(dirname)
            # The list comprehension is a workaround for an obscure translation
            # bug.
            return space.newlist_bytes([x for x in result])
    except OSError as e:
        raise wrap_oserror2(space, e, w_dirname)

def pipe(space):
    "Create a pipe.  Returns (read_end, write_end)."
    try:
        fd1, fd2 = os.pipe()
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.newtuple([space.wrap(fd1), space.wrap(fd2)])

@unwrap_spec(mode=c_int)
def chmod(space, w_path, mode):
    "Change the access permissions of a file."
    try:
        dispatch_filename(rposix.chmod)(space, w_path, mode)
    except OSError as e:
        raise wrap_oserror2(space, e, w_path)

@unwrap_spec(mode=c_int)
def fchmod(space, w_fd, mode):
    """Change the access permissions of the file given by file
descriptor fd."""
    fd = space.c_filedescriptor_w(w_fd)
    try:
        os.fchmod(fd, mode)
    except OSError as e:
        raise wrap_oserror(space, e)

def rename(space, w_old, w_new):
    "Rename a file or directory."
    try:
        dispatch_filename_2(rposix.rename)(space, w_old, w_new)
    except OSError as e:
        raise wrap_oserror(space, e)

@unwrap_spec(mode=c_int)
def mkfifo(space, w_filename, mode=0666):
    """Create a FIFO (a POSIX named pipe)."""
    try:
        dispatch_filename(rposix.mkfifo)(space, w_filename, mode)
    except OSError as e:
        raise wrap_oserror2(space, e, w_filename)

@unwrap_spec(mode=c_int, device=c_int)
def mknod(space, w_filename, mode=0600, device=0):
    """Create a filesystem node (file, device special file or named pipe)
named filename. mode specifies both the permissions to use and the
type of node to be created, being combined (bitwise OR) with one of
S_IFREG, S_IFCHR, S_IFBLK, and S_IFIFO. For S_IFCHR and S_IFBLK,
device defines the newly created device special file (probably using
os.makedev()), otherwise it is ignored."""
    try:
        dispatch_filename(rposix.mknod)(space, w_filename, mode, device)
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
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.wrap(pid)

@unwrap_spec(pid=c_int, sig=c_int)
def kill(space, pid, sig):
    "Kill a process with a signal."
    try:
        rposix.kill(pid, sig)
    except OSError as e:
        raise wrap_oserror(space, e)

@unwrap_spec(pgid=c_int, sig=c_int)
def killpg(space, pgid, sig):
    "Kill a process group with a signal."
    try:
        os.killpg(pgid, sig)
    except OSError as e:
        raise wrap_oserror(space, e)

def abort(space):
    """Abort the interpreter immediately.  This 'dumps core' or otherwise fails
in the hardest way possible on the hosting operating system."""
    import signal
    rposix.kill(os.getpid(), signal.SIGABRT)

@unwrap_spec(src='str0', dst='str0')
def link(space, src, dst):
    "Create a hard link to a file."
    try:
        os.link(src, dst)
    except OSError as e:
        raise wrap_oserror(space, e)

def symlink(space, w_src, w_dst):
    "Create a symbolic link pointing to src named dst."
    try:
        dispatch_filename_2(rposix.symlink)(space, w_src, w_dst)
    except OSError as e:
        raise wrap_oserror(space, e)

@unwrap_spec(path='str0')
def readlink(space, path):
    "Return a string representing the path to which the symbolic link points."
    try:
        result = os.readlink(path)
    except OSError as e:
        raise wrap_oserror(space, e, path)
    return space.wrap(result)

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
    except OSError as e:
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
    except OSError as e:
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
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.newtuple([space.wrap(pid), space.wrap(status)])

@unwrap_spec(status=c_int)
def _exit(space, status):
    os._exit(status)

def execv(space, w_command, w_args):
    """ execv(path, args)

Execute an executable path with arguments, replacing current process.

        path: path of executable file
        args: iterable of strings
    """
    execve(space, w_command, w_args, None)

def _env2interp(space, w_env):
    env = {}
    w_keys = space.call_method(w_env, 'keys')
    for w_key in space.unpackiterable(w_keys):
        w_value = space.getitem(w_env, w_key)
        env[space.str0_w(w_key)] = space.str0_w(w_value)
    return env

def execve(space, w_command, w_args, w_env):
    """ execve(path, args, env)

Execute a path with arguments and environment, replacing current process.

        path: path of executable file
        args: iterable of arguments
        env: dictionary of strings mapping to strings
    """
    command = fsencode_w(space, w_command)
    try:
        args_w = space.unpackiterable(w_args)
        if len(args_w) < 1:
            raise oefmt(space.w_ValueError,
                        "execv() must have at least one argument")
        args = [fsencode_w(space, w_arg) for w_arg in args_w]
    except OperationError as e:
        if not e.match(space, space.w_TypeError):
            raise
        raise oefmt(space.w_TypeError,
                    "execv() arg 2 must be an iterable of strings")
    #
    if w_env is None:    # when called via execv() above
        try:
            os.execv(command, args)
        except OSError as e:
            raise wrap_oserror(space, e)
    else:
        env = _env2interp(space, w_env)
        try:
            os.execve(command, args, env)
        except OSError as e:
            raise wrap_oserror(space, e)

@unwrap_spec(mode=int, path='str0')
def spawnv(space, mode, path, w_args):
    args = [space.str0_w(w_arg) for w_arg in space.unpackiterable(w_args)]
    try:
        ret = os.spawnv(mode, path, args)
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.wrap(ret)

@unwrap_spec(mode=int, path='str0')
def spawnve(space, mode, path, w_args, w_env):
    args = [space.str0_w(w_arg) for w_arg in space.unpackiterable(w_args)]
    env = _env2interp(space, w_env)
    try:
        ret = os.spawnve(mode, path, args, env)
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.wrap(ret)

def utime(space, w_path, w_tuple):
    """ utime(path, (atime, mtime))
utime(path, None)

Set the access and modified time of the file to the given values.  If the
second form is used, set the access and modified times to the current time.
    """
    if space.is_w(w_tuple, space.w_None):
        try:
            dispatch_filename(rposix.utime, 1)(space, w_path, None)
            return
        except OSError as e:
            raise wrap_oserror2(space, e, w_path)
    try:
        msg = "utime() arg 2 must be a tuple (atime, mtime) or None"
        args_w = space.fixedview(w_tuple)
        if len(args_w) != 2:
            raise oefmt(space.w_TypeError, msg)
        actime = space.float_w(args_w[0], allow_conversion=False)
        modtime = space.float_w(args_w[1], allow_conversion=False)
        dispatch_filename(rposix.utime, 2)(space, w_path, (actime, modtime))
    except OSError as e:
        raise wrap_oserror2(space, e, w_path)
    except OperationError as e:
        if not e.match(space, space.w_TypeError):
            raise
        raise oefmt(space.w_TypeError, msg)

def uname(space):
    """ uname() -> (sysname, nodename, release, version, machine)

    Return a tuple identifying the current operating system.
    """
    try:
        r = os.uname()
    except OSError as e:
        raise wrap_oserror(space, e)
    l_w = [space.wrap(i) for i in [r[0], r[1], r[2], r[3], r[4]]]
    return space.newtuple(l_w)

def getuid(space):
    """ getuid() -> uid

    Return the current process's user id.
    """
    return wrap_uid(space, os.getuid())

@unwrap_spec(arg=c_uid_t)
def setuid(space, arg):
    """ setuid(uid)

    Set the current process's user id.
    """
    try:
        os.setuid(arg)
    except OSError as e:
        raise wrap_oserror(space, e)

@unwrap_spec(arg=c_uid_t)
def seteuid(space, arg):
    """ seteuid(uid)

    Set the current process's effective user id.
    """
    try:
        os.seteuid(arg)
    except OSError as e:
        raise wrap_oserror(space, e)

@unwrap_spec(arg=c_gid_t)
def setgid(space, arg):
    """ setgid(gid)

    Set the current process's group id.
    """
    try:
        os.setgid(arg)
    except OSError as e:
        raise wrap_oserror(space, e)

@unwrap_spec(arg=c_gid_t)
def setegid(space, arg):
    """ setegid(gid)

    Set the current process's effective group id.
    """
    try:
        os.setegid(arg)
    except OSError as e:
        raise wrap_oserror(space, e)

@unwrap_spec(path='str0')
def chroot(space, path):
    """ chroot(path)

    Change root directory to path.
    """
    try:
        os.chroot(path)
    except OSError as e:
        raise wrap_oserror(space, e, path)
    return space.w_None

def getgid(space):
    """ getgid() -> gid

    Return the current process's group id.
    """
    return wrap_gid(space, os.getgid())

def getegid(space):
    """ getegid() -> gid

    Return the current process's effective group id.
    """
    return wrap_gid(space, os.getegid())

def geteuid(space):
    """ geteuid() -> euid

    Return the current process's effective user id.
    """
    return wrap_uid(space, os.geteuid())

def getgroups(space):
    """ getgroups() -> list of group IDs

    Return list of supplemental group IDs for the process.
    """
    try:
        list = os.getgroups()
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.newlist([wrap_gid(space, e) for e in list])

def setgroups(space, w_list):
    """ setgroups(list)

    Set the groups of the current process to list.
    """
    list = []
    for w_gid in space.unpackiterable(w_list):
        list.append(space.c_uid_t_w(w_gid))
    try:
        os.setgroups(list[:])
    except OSError as e:
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
    except OSError as e:
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
    except OSError as e:
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
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.wrap(pgid)

@unwrap_spec(pid=c_int, pgrp=c_int)
def setpgid(space, pid, pgrp):
    """ setpgid(pid, pgrp)

    Call the system call setpgid().
    """
    try:
        os.setpgid(pid, pgrp)
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.w_None

@unwrap_spec(ruid=c_uid_t, euid=c_uid_t)
def setreuid(space, ruid, euid):
    """ setreuid(ruid, euid)

    Set the current process's real and effective user ids.
    """
    try:
        os.setreuid(ruid, euid)
    except OSError as e:
        raise wrap_oserror(space, e)

@unwrap_spec(rgid=c_gid_t, egid=c_gid_t)
def setregid(space, rgid, egid):
    """ setregid(rgid, egid)

    Set the current process's real and effective group ids.
    """
    try:
        os.setregid(rgid, egid)
    except OSError as e:
        raise wrap_oserror(space, e)

@unwrap_spec(pid=c_int)
def getsid(space, pid):
    """ getsid(pid) -> sid

    Call the system call getsid().
    """
    try:
        sid = os.getsid(pid)
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.wrap(sid)

def setsid(space):
    """ setsid()

    Call the system call setsid().
    """
    try:
        os.setsid()
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.w_None

@unwrap_spec(fd=c_int)
def tcgetpgrp(space, fd):
    """ tcgetpgrp(fd) -> pgid

    Return the process group associated with the terminal given by a fd.
    """
    try:
        pgid = os.tcgetpgrp(fd)
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.wrap(pgid)

@unwrap_spec(fd=c_int, pgid=c_int)
def tcsetpgrp(space, fd, pgid):
    """ tcsetpgrp(fd, pgid)

    Set the process group associated with the terminal given by a fd.
    """
    try:
        os.tcsetpgrp(fd, pgid)
    except OSError as e:
        raise wrap_oserror(space, e)

def getresuid(space):
    """ getresuid() -> (ruid, euid, suid)

    Get tuple of the current process's real, effective, and saved user ids.
    """
    try:
        (ruid, euid, suid) = os.getresuid()
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.newtuple([wrap_uid(space, ruid),
                           wrap_uid(space, euid),
                           wrap_uid(space, suid)])

def getresgid(space):
    """ getresgid() -> (rgid, egid, sgid)

    Get tuple of the current process's real, effective, and saved group ids.
    """
    try:
        (rgid, egid, sgid) = os.getresgid()
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.newtuple([wrap_gid(space, rgid),
                           wrap_gid(space, egid),
                           wrap_gid(space, sgid)])

@unwrap_spec(ruid=c_uid_t, euid=c_uid_t, suid=c_uid_t)
def setresuid(space, ruid, euid, suid):
    """ setresuid(ruid, euid, suid)

    Set the current process's real, effective, and saved user ids.
    """
    try:
        os.setresuid(ruid, euid, suid)
    except OSError as e:
        raise wrap_oserror(space, e)

@unwrap_spec(rgid=c_gid_t, egid=c_gid_t, sgid=c_gid_t)
def setresgid(space, rgid, egid, sgid):
    """ setresgid(rgid, egid, sgid)
    
    Set the current process's real, effective, and saved group ids.
    """
    try:
        os.setresgid(rgid, egid, sgid)
    except OSError as e:
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
        return space.wrap(os.ttyname(fd))
    except OSError as e:
        raise wrap_oserror(space, e)


def confname_w(space, w_name, namespace):
    # XXX slightly non-nice, reuses the sysconf of the underlying os module
    if space.isinstance_w(w_name, space.w_basestring):
        try:
            num = namespace[space.str_w(w_name)]
        except KeyError:
            raise oefmt(space.w_ValueError, "unrecognized configuration name")
    else:
        num = space.int_w(w_name)
    return num

def sysconf(space, w_name):
    num = confname_w(space, w_name, os.sysconf_names)
    try:
        res = os.sysconf(num)
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.wrap(res)

@unwrap_spec(fd=c_int)
def fpathconf(space, fd, w_name):
    num = confname_w(space, w_name, os.pathconf_names)
    try:
        res = os.fpathconf(fd, num)
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.wrap(res)

@unwrap_spec(path='str0')
def pathconf(space, path, w_name):
    num = confname_w(space, w_name, os.pathconf_names)
    try:
        res = os.pathconf(path, num)
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.wrap(res)

def confstr(space, w_name):
    num = confname_w(space, w_name, os.confstr_names)
    try:
        res = os.confstr(num)
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.wrap(res)

@unwrap_spec(path='str0', uid=c_uid_t, gid=c_gid_t)
def chown(space, path, uid, gid):
    """Change the owner and group id of path to the numeric uid and gid."""
    try:
        os.chown(path, uid, gid)
    except OSError as e:
        raise wrap_oserror(space, e, path)

@unwrap_spec(path='str0', uid=c_uid_t, gid=c_gid_t)
def lchown(space, path, uid, gid):
    """Change the owner and group id of path to the numeric uid and gid.
This function will not follow symbolic links."""
    try:
        os.lchown(path, uid, gid)
    except OSError as e:
        raise wrap_oserror(space, e, path)

@unwrap_spec(uid=c_uid_t, gid=c_gid_t)
def fchown(space, w_fd, uid, gid):
    """Change the owner and group id of the file given by file descriptor
fd to the numeric uid and gid."""
    fd = space.c_filedescriptor_w(w_fd)
    try:
        os.fchown(fd, uid, gid)
    except OSError as e:
        raise wrap_oserror(space, e)

def getloadavg(space):
    try:
        load = os.getloadavg()
    except OSError:
        raise oefmt(space.w_OSError, "Load averages are unobtainable")
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
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.wrap(res)

@unwrap_spec(n=int)
def urandom(space, n):
    """urandom(n) -> str

    Return a string of n random bytes suitable for cryptographic use.
    """
    context = get(space).random_context
    try:
        return space.wrap(rurandom.urandom(context, n))
    except OSError as e:
        raise wrap_oserror(space, e)

def ctermid(space):
    """ctermid() -> string

    Return the name of the controlling terminal for this process.
    """
    return space.wrap(os.ctermid())
