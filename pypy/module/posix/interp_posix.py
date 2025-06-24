import os
import sys

from rpython.rlib import rposix, rposix_stat, rstring
from rpython.rlib import objectmodel, rurandom
from rpython.rlib.objectmodel import specialize, not_rpython
from rpython.rlib.rarithmetic import r_longlong, intmask, r_uint
from rpython.rlib.unroll import unrolling_iterable
from rpython.rlib.rutf8 import codepoints_in_utf8

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
# this looks like a typo but is not, it goes to visit_c_uid_t and there
# is no visit_c_gid_t
c_gid_t = 'c_uid_t'

def wrap_uid(space, uid):
    if uid <= r_uint(sys.maxint):
        return space.newint(intmask(uid))
    else:
        return space.newint(uid)     # an unsigned number
wrap_gid = wrap_uid

class FileEncoder(object):
    is_unicode = True

    def __init__(self, space, w_obj):
        self.space = space
        self.w_obj = w_obj

    def as_bytes(self):
        return self.space.fsencode_w(self.w_obj)

    def as_utf8(self):
        ret = self.space.utf8_w(self.w_obj)
        if '\x00' in ret:
            raise oefmt(self.space.w_TypeError, "embedded null character")
        return ret

class FileDecoder(object):
    is_unicode = False

    def __init__(self, space, w_obj):
        self.space = space
        self.w_obj = w_obj

    def as_bytes(self):
        return self.space.fsencode_w(self.w_obj)

    def as_utf8(self):
        ret = self.space.utf8_w(self.w_obj)
        if '\x00' in ret:
            raise oefmt(self.space.w_TypeError, "embedded null character")
        return ret

@specialize.memo()
def dispatch_filename(func, tag=0):
    @specialize.argtype(1)
    def dispatch(space, w_fname, *args):
        if space.isinstance_w(w_fname, space.w_unicode):
            fname = FileEncoder(space, w_fname)
            return func(fname, *args)
        else:
            fname = space.bytes0_w(w_fname)
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

def u2utf8(space, u_str):
    return space.newutf8(u_str.encode('utf-8'), len(u_str))

@unwrap_spec(flag=c_int, mode=c_int)
def open(space, w_fname, flag, mode=0777):
    """Open a file (for low level IO).
Return a file descriptor (a small integer)."""
    from rpython.rlib import rposix
    try:
        fd = dispatch_filename(rposix.open)(
            space, w_fname, flag, mode)
    except OSError as e:
        raise wrap_oserror2(space, e, w_fname)
    return space.newint(fd)

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
        return space.newint(pos)

@unwrap_spec(fd=c_int)
def isatty(space, fd):
    """Return True if 'fd' is an open file descriptor connected to the
slave end of a terminal."""
    try:
        res = os.isatty(fd)
    except OSError as e:
        raise wrap_oserror(space, e)
    else:
        return space.newbool(res)

@unwrap_spec(fd=c_int, buffersize=int)
def read(space, fd, buffersize):
    """Read data from a file descriptor."""
    try:
        s = os.read(fd, buffersize)
    except OSError as e:
        raise wrap_oserror(space, e)
    else:
        return space.newbytes(s)

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
        return space.newint(res)

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
            w_error = space.call_function(space.w_OSError, space.newint(e.errno),
                                          space.newtext(e.strerror),
                                          space.newtext(e.filename))
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
    stat_float_times = space.fromcache(StatState).stat_float_times
    for i, (name, TYPE) in FIELDS:
        if i < rposix_stat.N_INDEXABLE_FIELDS:
            # get the first 10 items by indexing; this gives us
            # 'st_Xtime' as an integer, too
            w_value = space.newint(st[i])
            lst[i] = w_value
        else:
            break

    w_tuple = space.newtuple(lst)
    w_stat_result = space.getattr(space.getbuiltinmodule(os.name),
                                  space.newtext('stat_result'))
    # this is a bit of a hack: circumvent the huge mess of structseq_new and a
    # dict argument and just build the object ourselves. then it stays nicely
    # virtual and eg. os.islink can just get the field from the C struct and be
    # done.
    w_tup_new = space.getattr(space.w_tuple,
                              space.newtext('__new__'))
    w_result = space.call_function(w_tup_new, w_stat_result, w_tuple)
    for i, (name, TYPE) in FIELDS:
        if i < rposix_stat.N_INDEXABLE_FIELDS:
            continue
        elif name.startswith('st_'):    # exclude 'nsec_Xtime'
            w_value = space.newint(getattr(st, name))
            w_result.setdictvalue(space, name, w_value)

    # non-rounded values for name-based access
    if stat_float_times:
        w_result.setdictvalue(space, 'st_atime', space.newfloat(st.st_atime))
        w_result.setdictvalue(space, 'st_mtime', space.newfloat(st.st_mtime))
        w_result.setdictvalue(space, 'st_ctime', space.newfloat(st.st_ctime))
    else:
        w_result.setdictvalue(space, 'st_atime', space.newint(st[7]))
        w_result.setdictvalue(space, 'st_mtime', space.newint(st[8]))
        w_result.setdictvalue(space, 'st_ctime', space.newint(st[9]))
    return w_result


def build_statvfs_result(space, st):
    vals_w = [None] * len(rposix_stat.STATVFS_FIELDS)
    for i, (name, _) in STATVFS_FIELDS:
        vals_w[i] = space.newint(getattr(st, name))
    # f_fsid is not python2-compatible
    w_tuple = space.newtuple(vals_w[:-1])
    w_statvfs_result = space.getattr(space.getbuiltinmodule(os.name), space.newtext('statvfs_result'))
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
        return space.newbool(state.stat_float_times)
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
        return space.newint(newfd)

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
        return space.newbool(ok)


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
        return space.newtuple([space.newfloat(times[0]),
                               space.newfloat(times[1]),
                               space.newfloat(times[2]),
                               space.newfloat(times[3]),
                               space.newfloat(times[4])])

@unwrap_spec(cmd='text0')
def system(space, cmd):
    """Execute the command (a string) in a subshell."""
    try:
        rc = os.system(cmd)
    except OSError as e:
        raise wrap_oserror(space, e)
    else:
        return space.newint(rc)

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
    path = space.fsencode_w(w_path)
    try:
        fullpath = rposix.getfullpathname(path)
    except OSError as e:
        raise wrap_oserror(space, e, path)
    if space.isinstance_w(w_path, space.w_unicode):
        ulen = codepoints_in_utf8(fullpath)
        return space.newutf8(fullpath, ulen)
    else:
        return space.newbytes(fullpath)

def getcwd(space):
    """Return the current working directory."""
    try:
        cur = os.getcwd()
    except OSError as e:
        raise wrap_oserror(space, e)
    else:
        return space.newtext(cur)

if _WIN32:
    def getcwdu(space):
        """Return the current working directory as a unicode string."""
        try:
            cur = os.getcwdu()
        except OSError as e:
            raise wrap_oserror(space, e)
        else:
            return u2utf8(space, cur)
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
    return space.newtext(text)

def getlogin(space):
    """Return the currently logged in user."""
    try:
        cur = os.getlogin()
    except OSError as e:
        raise wrap_oserror(space, e)
    else:
        return space.newfilename(cur)

# ____________________________________________________________

def getstatfields(space):
    # for app_posix.py: export the list of 'st_xxx' names that we know
    # about at RPython level
    return space.newlist([space.newtext(name) for _, (name, _) in STAT_FIELDS])


class State:
    def __init__(self, space):
        self.space = space
        self.w_environ = space.newdict()
    def startup(self, space):
        _convertenviron(space, self.w_environ)
    def _freeze_(self):
        # don't capture the environment in the translated pypy
        self.space.call_method(self.w_environ, 'clear')
        return True

def get(space):
    return space.fromcache(State)

def _convertenviron(space, w_env):
    space.call_method(w_env, 'clear')
    for key, value in os.environ.items():
        space.setitem(w_env, space.newtext(key), space.newtext(value))

@unwrap_spec(name='text0', value='text0')
def putenv(space, name, value):
    """Change or add an environment variable."""
    if _WIN32:
        # Search from index 1 because on Windows starting '=' is allowed
        # in general (see os.chdir which sets '=D:' for chdir(r'D:\temp')
        # However it is a bit pointless here since the putenv system call
        # hides the key/value.
        # GetEnvironmentVariable/SetEnvironmentVariable will expose them,
        # and as is mentioned in https://github.com/python/cpython/pull/2325#discussion_r674746677,
        # someday the syscall may change to SetEnvironmentVariable here.
        if len(name) == 0 or '=' in name[1:]:
            raise oefmt(space.w_ValueError, "illegal environment variable name")
        if len(name) > _MAX_ENV:
            raise oefmt(space.w_ValueError,
                        "the environment variable is longer than %d bytes",
                        _MAX_ENV)
        if not objectmodel.we_are_translated() and value == '':
            # special case: on Windows, _putenv("NAME=") really means that
            # we want to delete NAME.  So that's what the os.environ[name]=''
            # below will do after translation.  But before translation, it
            # will cache the environment value '' instead of <missing> and
            # then return that.  We need to avoid that.
            del os.environ[name]
            return
    else:
        if '=' in name:
            raise oefmt(space.w_ValueError, "illegal environment variable name")

    try:
        os.environ[name] = value
    except OSError as e:
        raise wrap_oserror(space, e)

@unwrap_spec(name='text0')
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
            # NOTE: 'result' can be either a list of str or a list of
            # unicodes, depending on the platform
            w_fs_encoding = getfilesystemencoding(space)
            len_result = len(result)
            result_w = [None] * len_result
            for i in range(len_result):
                res = result[i]
                if isinstance(res, str):
                    w_bytes = space.newtext(res)
                    try:
                        w_res = space.call_method(w_bytes,
                                                  "decode", w_fs_encoding)
                    except OperationError as e:
                        # fall back to the original byte string
                        if e.async(space):
                            raise
                        w_res = w_bytes
                elif isinstance(res, unicode):
                    w_res = u2utf8(space, res)
                else:
                    assert False
                result_w[i] = w_res
            return space.newlist(result_w)
        else:
            dirname = space.bytes0_w(w_dirname)
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
    return space.newtuple2(space.newint(fd1), space.newint(fd2))

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
    return space.newint(prevmask)

def getpid(space):
    "Return the current process id."
    try:
        pid = os.getpid()
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.newint(pid)

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

@unwrap_spec(src='fsencode', dst='fsencode')
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

@unwrap_spec(path='fsencode')
def readlink(space, path):
    "Return a string representing the path to which the symbolic link points."
    try:
        result = os.readlink(path)
    except OSError as e:
        raise wrap_oserror(space, e, path)
    return space.newtext(result)

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

@not_rpython
def add_fork_hook(where, hook):
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
    return space.newint(pid)

def openpty(space):
    "Open a pseudo-terminal, returning open fd's for both master and slave end."
    try:
        master_fd, slave_fd = os.openpty()
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.newtuple2(space.newint(master_fd), space.newint(slave_fd))

def forkpty(space):
    pid, master_fd = _run_forking_function(space, "P")
    return space.newtuple2(space.newint(pid),
                           space.newint(master_fd))

@unwrap_spec(pid=c_int, options=c_int)
def waitpid(space, pid, options):
    """ waitpid(pid, options) -> (pid, status)

    Wait for completion of a given child process.
    """
    try:
        pid, status = os.waitpid(pid, options)
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.newtuple2(space.newint(pid), space.newint(status))

@unwrap_spec(status=c_int)
def _exit(space, status):
    os._exit(status)

@unwrap_spec(command='fsencode')
def execv(space, command, w_args):
    """ execv(path, args)

Execute an executable path with arguments, replacing current process.

        path: path of executable file
        args: iterable of strings
    """
    execve(space, command, w_args, None)

def _env2interp(space, w_env):
    env = {}
    w_keys = space.call_method(w_env, 'keys')
    for w_key in space.unpackiterable(w_keys):
        w_value = space.getitem(w_env, w_key)
        env[space.text0_w(w_key)] = space.text0_w(w_value)
    return env

def _env2interp(space, w_env):
    env = {}
    w_keys = space.call_method(w_env, 'keys')
    for w_key in space.unpackiterable(w_keys):
        w_value = space.getitem(w_env, w_key)
        key = space.text0_w(w_key)
        val = space.text0_w(w_value)
        # Search from index 1 because on Windows starting '=' is allowed for
        # defining hidden environment variables
        if len(key) == 0 or '=' in key[1:]:
            raise oefmt(space.w_ValueError,
                "illegal environment variable name")
        env[key] = val
    return env


@unwrap_spec(command='fsencode')
def execve(space, command, w_args, w_env):
    """ execve(path, args, env)

Execute a path with arguments and environment, replacing current process.

        path: path of executable file
        args: iterable of arguments
        env: dictionary of strings mapping to strings
    """
    try:
        args_w = space.unpackiterable(w_args)
        if len(args_w) < 1:
            raise oefmt(space.w_ValueError,
                        "execv() must have at least one argument")
        args = [space.fsencode_w(w_arg) for w_arg in args_w]
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

@unwrap_spec(mode=int, path='fsencode')
def spawnv(space, mode, path, w_args):
    args = [space.fsencode_w(w_arg) for w_arg in space.unpackiterable(w_args)]
    try:
        ret = os.spawnv(mode, path, args)
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.newint(ret)

@unwrap_spec(mode=int, path='fsencode')
def spawnve(space, mode, path, w_args, w_env):
    args = [space.fsencode_w(w_arg) for w_arg in space.unpackiterable(w_args)]
    env = _env2interp(space, w_env)
    try:
        ret = os.spawnve(mode, path, args, env)
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.newint(ret)

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
    l_w = [space.newfilename(i) for i in [r[0], r[1], r[2], r[3], r[4]]]
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

@unwrap_spec(path='fsencode')
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

@unwrap_spec(username='text', gid=c_gid_t)
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
    return space.newint(os.getpgrp())

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
    return space.newint(os.getppid())

@unwrap_spec(pid=c_int)
def getpgid(space, pid):
    """ getpgid(pid) -> pgid

    Call the system call getpgid().
    """
    try:
        pgid = os.getpgid(pid)
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.newint(pgid)

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
    return space.newint(sid)

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
    return space.newint(pgid)

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
            return space.newint(getattr(os, name)(status))
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
        return space.newfilename(os.ttyname(fd))
    except OSError as e:
        raise wrap_oserror(space, e)


def confname_w(space, w_name, namespace):
    # XXX slightly non-nice, reuses the sysconf of the underlying os module
    if space.isinstance_w(w_name, space.w_basestring):
        try:
            num = namespace[space.text_w(w_name)]
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
    return space.newint(res)

@unwrap_spec(fd=c_int)
def fpathconf(space, fd, w_name):
    num = confname_w(space, w_name, os.pathconf_names)
    try:
        res = os.fpathconf(fd, num)
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.newint(res)

@unwrap_spec(path='fsencode')
def pathconf(space, path, w_name):
    num = confname_w(space, w_name, os.pathconf_names)
    try:
        res = os.pathconf(path, num)
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.newint(res)

def confstr(space, w_name):
    num = confname_w(space, w_name, os.confstr_names)
    try:
        res = os.confstr(num)
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.newtext(res)

@unwrap_spec(path='fsencode', uid=c_uid_t, gid=c_gid_t)
def chown(space, path, uid, gid):
    """Change the owner and group id of path to the numeric uid and gid."""
    try:
        os.chown(path, uid, gid)
    except OSError as e:
        raise wrap_oserror(space, e, path)

@unwrap_spec(path='fsencode', uid=c_uid_t, gid=c_gid_t)
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
    return space.newtuple([space.newfloat(load[0]),
                           space.newfloat(load[1]),
                           space.newfloat(load[2])])

@unwrap_spec(major=c_int, minor=c_int)
def makedev(space, major, minor):
    result = os.makedev(major, minor)
    return space.newint(result)

@unwrap_spec(device="c_uint")
def major(space, device):
    result = os.major(intmask(device))
    return space.newint(result)

@unwrap_spec(device="c_uint")
def minor(space, device):
    result = os.minor(intmask(device))
    return space.newint(result)

@unwrap_spec(inc=c_int)
def nice(space, inc):
    "Decrease the priority of process by inc and return the new priority."
    try:
        res = os.nice(inc)
    except OSError as e:
        raise wrap_oserror(space, e)
    return space.newint(res)

class SigCheck:
    pass
_sigcheck = SigCheck()
def _signal_checker():
    _sigcheck.space.getexecutioncontext().checksignals()

@unwrap_spec(n=int)
def urandom(space, n):
    """urandom(n) -> str

    Return a string of n random bytes suitable for cryptographic use.
    """
    try:
        # urandom() takes a final argument that should be a regular function,
        # not a bound method like 'getexecutioncontext().checksignals'.
        # Otherwise, we can't use it from several independent places.
        _sigcheck.space = space
        return space.newbytes(rurandom.urandom(n, _signal_checker))
    except OSError as e:
        # CPython raises NotImplementedError if /dev/urandom cannot be found.
        # To maximize compatibility, we should also raise NotImplementedError
        # and not OSError (although CPython also raises OSError in case it
        # could open /dev/urandom but there are further problems).
        raise wrap_oserror(space, e,
            w_exception_class=space.w_NotImplementedError)

def ctermid(space):
    """ctermid() -> string

    Return the name of the controlling terminal for this process.
    """
    return space.newfilename(os.ctermid())
