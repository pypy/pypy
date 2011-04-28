from pypy.interpreter.gateway import unwrap_spec, NoneNotWrapped
from pypy.rlib import rposix, objectmodel
from pypy.rlib.objectmodel import specialize
from pypy.rlib.rarithmetic import r_longlong
from pypy.rlib.unroll import unrolling_iterable
from pypy.interpreter.error import OperationError, wrap_oserror, wrap_oserror2
from pypy.interpreter.error import operationerrfmt
from pypy.rpython.module.ll_os import RegisterOs
from pypy.rpython.module import ll_os_stat
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.tool import rffi_platform
from pypy.translator.tool.cbuild import ExternalCompilationInfo

import os, sys
_WIN = sys.platform == 'win32'

c_int = "c_int"

# CPython 2.7 semantics are too messy to follow exactly,
# e.g. setuid(-2) works on 32-bit but not on 64-bit.  As a result,
# we decided to just accept any 'int', i.e. any C signed long.
c_uid_t = int
c_gid_t = int

class FileEncoder(object):
    def __init__(self, space, w_obj):
        self.space = space
        self.w_obj = w_obj

    def as_bytes(self):
        from pypy.module.sys.interp_encoding import getfilesystemencoding
        space = self.space
        w_bytes = space.call_method(self.w_obj, 'encode',
                                    getfilesystemencoding(space))
        return space.str_w(w_bytes)

    def as_unicode(self):
        return self.space.unicode_w(self.w_obj)

class FileDecoder(object):
    def __init__(self, space, w_obj):
        self.space = space
        self.w_obj = w_obj

    def as_bytes(self):
        return self.space.str_w(self.w_obj)

    def as_unicode(self):
        from pypy.module.sys.interp_encoding import getfilesystemencoding
        space = self.space
        w_unicode = space.call_method(self.w_obj, 'decode',
                                      getfilesystemencoding(space))
        return space.unicode_w(w_unicode)

@specialize.memo()
def dispatch_filename(func, tag=0):
    def dispatch(space, w_fname, *args):
        if space.isinstance_w(w_fname, space.w_unicode):
            fname = FileEncoder(space, w_fname)
            return func(fname, *args)
        else:
            fname = space.str_w(w_fname)
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
    except OSError, e:
        raise wrap_oserror2(space, e, w_fname)
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
        return space.wrap(s)

@unwrap_spec(fd=c_int, data='bufferstr')
def write(space, fd, data):
    """Write a string to a file descriptor.  Return the number of bytes
actually written, which may be smaller than len(data)."""
    try:
        res = os.write(fd, data)
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
    """Truncate a file to a specified length."""
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

# For LL backends, expose all fields.
# For OO backends, only the portable fields (the first 10).
STAT_FIELDS = unrolling_iterable(enumerate(ll_os_stat.STAT_FIELDS))
PORTABLE_STAT_FIELDS = unrolling_iterable(
                                 enumerate(ll_os_stat.PORTABLE_STAT_FIELDS))

def build_stat_result(space, st):
    if space.config.translation.type_system == 'ootype':
        FIELDS = PORTABLE_STAT_FIELDS
    else:
        FIELDS = STAT_FIELDS    # also when not translating at all
    lst = [None] * ll_os_stat.N_INDEXABLE_FIELDS
    w_keywords = space.newdict()
    stat_float_times = space.fromcache(StatState).stat_float_times
    for i, (name, TYPE) in FIELDS:
        value = getattr(st, name)
        if name in ('st_atime', 'st_mtime', 'st_ctime'):
            value = int(value)   # rounded to an integer for indexed access
        w_value = space.wrap(value)
        if i < ll_os_stat.N_INDEXABLE_FIELDS:
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

@unwrap_spec(fd=c_int)
def fstat(space, fd):
    """Perform a stat system call on the file referenced to by an open
file descriptor."""
    try:
        st = os.fstat(fd)
    except OSError, e:
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
        st = dispatch_filename(rposix.stat)(space, w_path)
    except OSError, e:
        raise wrap_oserror2(space, e, w_path)
    else:
        return build_stat_result(space, st)

def lstat(space, w_path):
    "Like stat(path), but do no follow symbolic links."
    try:
        st = dispatch_filename(rposix.lstat)(space, w_path)
    except OSError, e:
        raise wrap_oserror2(space, e, w_path)
    else:
        return build_stat_result(space, st)

class StatState(object):
    def __init__(self, space):
        self.stat_float_times = True

def stat_float_times(space, w_value=NoneNotWrapped):
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
    except OSError, e:
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

@unwrap_spec(cmd=str)
def system(space, cmd):
    """Execute the command (a string) in a subshell."""
    try:
        rc = os.system(cmd)
    except OSError, e:
        raise wrap_oserror(space, e)
    else:
        return space.wrap(rc)

def unlink(space, w_path):
    """Remove a file (same as remove(path))."""
    try:
        dispatch_filename(rposix.unlink)(space, w_path)
    except OSError, e:
        raise wrap_oserror2(space, e, w_path)

def remove(space, w_path):
    """Remove a file (same as unlink(path))."""
    try:
        dispatch_filename(rposix.unlink)(space, w_path)
    except OSError, e:
        raise wrap_oserror2(space, e, w_path)

def _getfullpathname(space, w_path):
    """helper for ntpath.abspath """
    try:
        if space.isinstance_w(w_path, space.w_unicode):
            path = FileEncoder(space, w_path)
            fullpath = rposix._getfullpathname(path)
            w_fullpath = space.wrap(fullpath)
        else:
            path = space.str_w(w_path)
            fullpath = rposix._getfullpathname(path)
            w_fullpath = space.wrap(fullpath)
    except OSError, e:
        raise wrap_oserror2(space, e, w_path)
    else:
        return w_fullpath

def getcwd(space):
    """Return the current working directory."""
    try:
        cur = os.getcwd()
    except OSError, e:
        raise wrap_oserror(space, e)
    else:
        return space.wrap(cur)

if sys.platform == 'win32':
    def getcwdu(space):
        """Return the current working directory as a unicode string."""
        try:
            cur = os.getcwdu()
        except OSError, e:
            raise wrap_oserror(space, e)
        else:
            return space.wrap(cur)
else:
    def getcwdu(space):
        """Return the current working directory as a unicode string."""
        filesystemencoding = space.sys.filesystemencoding
        return space.call_method(getcwd(space), 'decode',
                                 space.wrap(filesystemencoding))

def chdir(space, w_path):
    """Change the current working directory to the specified path."""
    try:
        dispatch_filename(rposix.chdir)(space, w_path)
    except OSError, e:
        raise wrap_oserror2(space, e, w_path)

@unwrap_spec(mode=c_int)
def mkdir(space, w_path, mode=0777):
    """Create a directory."""
    try:
        dispatch_filename(rposix.mkdir)(space, w_path, mode)
    except OSError, e:
        raise wrap_oserror2(space, e, w_path)

def rmdir(space, w_path):
    """Remove a directory."""
    try:
        dispatch_filename(rposix.rmdir)(space, w_path)
    except OSError, e:
        raise wrap_oserror2(space, e, w_path)

@unwrap_spec(errno=c_int)
def strerror(space, errno):
    """Translate an error code to a message string."""
    try:
        text = os.strerror(errno)
    except ValueError:
        raise OperationError(space.w_ValueError,
                             space.wrap("strerror() argument out of range"))
    return space.wrap(text)

# ____________________________________________________________

def getstatfields(space):
    # for app_posix.py: export the list of 'st_xxx' names that we know
    # about at RPython level
    if space.config.translation.type_system == 'ootype':
        FIELDS = PORTABLE_STAT_FIELDS
    else:
        FIELDS = STAT_FIELDS    # also when not translating at all
    return space.newlist([space.wrap(name) for name, _ in FIELDS])


class State:
    def __init__(self, space):
        self.space = space
        self.w_environ = space.newdict()
        if _WIN:
            self.cryptProviderPtr = lltype.malloc(
                rffi.CArray(HCRYPTPROV), 1, zero=True,
                flavor='raw', immortal=True)
    def startup(self, space):
        _convertenviron(space, self.w_environ)
    def _freeze_(self):
        # don't capture the environment in the translated pypy
        self.space.call_method(self.w_environ, 'clear')
        if _WIN:
            self.cryptProviderPtr[0] = HCRYPTPROV._default
        return True

def get(space):
    return space.fromcache(State)

def _convertenviron(space, w_env):
    space.call_method(w_env, 'clear')
    for key, value in os.environ.items():
        space.setitem(w_env, space.wrap(key), space.wrap(value))

@unwrap_spec(name=str, value=str)
def putenv(space, name, value):
    """Change or add an environment variable."""
    try:
        os.environ[name] = value
    except OSError, e:
        raise wrap_oserror(space, e)

@unwrap_spec(name=str)
def unsetenv(space, name):
    """Delete an environment variable."""
    try:
        del os.environ[name]
    except KeyError:
        pass
    except OSError, e:
        raise wrap_oserror(space, e)


def listdir(space, w_dirname):
    """Return a list containing the names of the entries in the directory.

\tpath: path of directory to list

The list is in arbitrary order.  It does not include the special
entries '.' and '..' even if they are present in the directory."""
    from pypy.module.sys.interp_encoding import getfilesystemencoding
    try:
        if space.isinstance_w(w_dirname, space.w_unicode):
            dirname = FileEncoder(space, w_dirname)
            result = rposix.listdir(dirname)
            w_fs_encoding = getfilesystemencoding(space)
            result_w = [
                space.call_method(space.wrap(s), "decode", w_fs_encoding)
                for s in result
            ]
        else:
            dirname = space.str_w(w_dirname)
            result = rposix.listdir(dirname)
            result_w = [space.wrap(s) for s in result]
    except OSError, e:
        raise wrap_oserror2(space, e, w_dirname)
    return space.newlist(result_w)

def pipe(space):
    "Create a pipe.  Returns (read_end, write_end)."
    try:
        fd1, fd2 = os.pipe()
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.newtuple([space.wrap(fd1), space.wrap(fd2)])

@unwrap_spec(mode=c_int)
def chmod(space, w_path, mode):
    "Change the access permissions of a file."
    try:
        dispatch_filename(rposix.chmod)(space, w_path, mode)
    except OSError, e:
        raise wrap_oserror2(space, e, w_path)

def rename(space, w_old, w_new):
    "Rename a file or directory."
    try:
        dispatch_filename_2(rposix.rename)(space, w_old, w_new)
    except OSError, e:
        raise wrap_oserror(space, e)

@unwrap_spec(mode=c_int)
def mkfifo(space, w_filename, mode=0666):
    """Create a FIFO (a POSIX named pipe)."""
    try:
        dispatch_filename(rposix.mkfifo)(space, w_filename, mode)
    except OSError, e:
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
    except OSError, e:
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
        os.kill(pid, sig)
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
    os.kill(os.getpid(), signal.SIGABRT)

@unwrap_spec(src=str, dst=str)
def link(space, src, dst):
    "Create a hard link to a file."
    try:
        os.link(src, dst)
    except OSError, e:
        raise wrap_oserror(space, e)

def symlink(space, w_src, w_dst):
    "Create a symbolic link pointing to src named dst."
    try:
        dispatch_filename_2(rposix.symlink)(space, w_src, w_dst)
    except OSError, e:
        raise wrap_oserror(space, e)

@unwrap_spec(path=str)
def readlink(space, path):
    "Return a string representing the path to which the symbolic link points."
    try:
        result = os.readlink(path)
    except OSError, e:
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

@specialize.arg(0)
def run_fork_hooks(where, space):
    for hook in get_fork_hooks(where):
        hook(space)

def fork(space):
    run_fork_hooks('before', space)

    try:
        pid = os.fork()
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

    return space.wrap(pid)

def openpty(space):
    "Open a pseudo-terminal, returning open fd's for both master and slave end."
    try:
        master_fd, slave_fd = os.openpty()
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.newtuple([space.wrap(master_fd), space.wrap(slave_fd)])

def forkpty(space):
    try:
        pid, master_fd = os.forkpty()
    except OSError, e:
        raise wrap_oserror(space, e)
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

@unwrap_spec(command=str)
def execv(space, command, w_args):
    """ execv(path, args)

Execute an executable path with arguments, replacing current process.

        path: path of executable file
        args: iterable of strings
    """
    try:
        args_w = space.unpackiterable(w_args)
        if len(args_w) < 1:
            w_msg = space.wrap("execv() must have at least one argument")
            raise OperationError(space.w_ValueError, w_msg)
        args = [space.str_w(w_arg) for w_arg in args_w]
    except OperationError, e:
        if not e.match(space, space.w_TypeError):
            raise
        msg = "execv() arg 2 must be an iterable of strings"
        raise OperationError(space.w_TypeError, space.wrap(str(msg)))
    try:
        os.execv(command, args)
    except OSError, e:
        raise wrap_oserror(space, e)

@unwrap_spec(command=str)
def execve(space, command, w_args, w_env):
    """ execve(path, args, env)

Execute a path with arguments and environment, replacing current process.

        path: path of executable file
        args: iterable of arguments
        env: dictionary of strings mapping to strings
    """
    args = [space.str_w(w_arg) for w_arg in space.unpackiterable(w_args)]
    env = {}
    w_keys = space.call_method(w_env, 'keys')
    for w_key in space.unpackiterable(w_keys):
        w_value = space.getitem(w_env, w_key)
        env[space.str_w(w_key)] = space.str_w(w_value)
    try:
        os.execve(command, args, env)
    except OSError, e:
        raise wrap_oserror(space, e)

@unwrap_spec(mode=int, path=str)
def spawnv(space, mode, path, w_args):
    args = [space.str_w(w_arg) for w_arg in space.unpackiterable(w_args)]
    try:
        ret = os.spawnv(mode, path, args)
    except OSError, e:
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
        except OSError, e:
            raise wrap_oserror2(space, e, w_path)
    try:
        msg = "utime() arg 2 must be a tuple (atime, mtime) or None"
        args_w = space.fixedview(w_tuple)
        if len(args_w) != 2:
            raise OperationError(space.w_TypeError, space.wrap(msg))
        actime = space.float_w(args_w[0])
        modtime = space.float_w(args_w[1])
        dispatch_filename(rposix.utime, 2)(space, w_path, (actime, modtime))
    except OSError, e:
        raise wrap_oserror2(space, e, w_path)
    except OperationError, e:
        if not e.match(space, space.w_TypeError):
            raise
        raise OperationError(space.w_TypeError, space.wrap(msg))

def setsid(space):
    """setsid() -> pid

    Creates a new session with this process as the leader.
    """
    try:
        result = os.setsid()
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.wrap(result)

def uname(space):
    """ uname() -> (sysname, nodename, release, version, machine)

    Return a tuple identifying the current operating system.
    """
    try:
        r = os.uname()
    except OSError, e:
        raise wrap_oserror(space, e)
    l_w = [space.wrap(i) for i in [r[0], r[1], r[2], r[3], r[4]]]
    return space.newtuple(l_w)

def getuid(space):
    """ getuid() -> uid

    Return the current process's user id.
    """
    return space.wrap(os.getuid())

@unwrap_spec(arg=int)
def setuid(space, arg):
    """ setuid(uid)

    Set the current process's user id.
    """
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
    try:
        os.setegid(arg)
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.w_None

@unwrap_spec(path=str)
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
    return space.newlist([space.wrap(e) for e in os.getgroups()])

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

def declare_new_w_star(name):
    if name in RegisterOs.w_star_returning_int:
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

for name in RegisterOs.w_star:
    if hasattr(os, name):
        func = declare_new_w_star(name)
        globals()[name] = func

@unwrap_spec(fd=c_int)
def ttyname(space, fd):
    try:
        return space.wrap(os.ttyname(fd))
    except OSError, e:
        raise wrap_oserror(space, e)

def confname_w(space, w_name, namespace):
    # XXX slightly non-nice, reuses the sysconf of the underlying os module
    if space.is_true(space.isinstance(w_name, space.w_basestring)):
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
    return space.wrap(os.sysconf(num))

@unwrap_spec(fd=c_int)
def fpathconf(space, fd, w_name):
    num = confname_w(space, w_name, os.pathconf_names)
    try:
        return space.wrap(os.fpathconf(fd, num))
    except OSError, e:
        raise wrap_oserror(space, e)

@unwrap_spec(path=str, uid=c_uid_t, gid=c_gid_t)
def chown(space, path, uid, gid):
    try:
        os.chown(path, uid, gid)
    except OSError, e:
        raise wrap_oserror(space, e, path)
    return space.w_None

@unwrap_spec(path=str, uid=c_uid_t, gid=c_gid_t)
def lchown(space, path, uid, gid):
    try:
        os.lchown(path, uid, gid)
    except OSError, e:
        raise wrap_oserror(space, e, path)
    return space.w_None

def getloadavg(space):
    try:
        load = os.getloadavg()
    except OSError, e:
        raise OperationError(space.w_OSError,
                             space.wrap("Load averages are unobtainable"))
    return space.newtuple([space.wrap(load[0]),
                           space.wrap(load[1]),
                           space.wrap(load[2])])

@unwrap_spec(major=c_int, minor=c_int)
def makedev(space, major, minor):
    result = os.makedev(major, minor)
    return space.wrap(result)

@unwrap_spec(device=c_int)
def major(space, device):
    result = os.major(device)
    return space.wrap(result)

@unwrap_spec(device=c_int)
def minor(space, device):
    result = os.minor(device)
    return space.wrap(result)

@unwrap_spec(inc=c_int)
def nice(space, inc):
    "Decrease the priority of process by inc and return the new priority."
    try:
        res = os.nice(inc)
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.wrap(res)

if _WIN:
    from pypy.rlib import rwin32

    eci = ExternalCompilationInfo(
        includes = ['windows.h', 'wincrypt.h'],
        libraries = ['advapi32'],
        )

    class CConfig:
        _compilation_info_ = eci
        PROV_RSA_FULL = rffi_platform.ConstantInteger(
            "PROV_RSA_FULL")
        CRYPT_VERIFYCONTEXT = rffi_platform.ConstantInteger(
            "CRYPT_VERIFYCONTEXT")

    globals().update(rffi_platform.configure(CConfig))

    HCRYPTPROV = rwin32.ULONG_PTR

    CryptAcquireContext = rffi.llexternal(
        'CryptAcquireContextA',
        [rffi.CArrayPtr(HCRYPTPROV),
         rwin32.LPCSTR, rwin32.LPCSTR, rwin32.DWORD, rwin32.DWORD],
        rwin32.BOOL,
        calling_conv='win',
        compilation_info=eci)

    CryptGenRandom = rffi.llexternal(
        'CryptGenRandom',
        [HCRYPTPROV, rwin32.DWORD, rffi.CArrayPtr(rwin32.BYTE)],
        rwin32.BOOL,
        calling_conv='win',
        compilation_info=eci)

    @unwrap_spec(n=int)
    def win32_urandom(space, n):
        """urandom(n) -> str

        Return a string of n random bytes suitable for cryptographic use.
        """

        if n < 0:
            raise OperationError(space.w_ValueError,
                                 space.wrap("negative argument not allowed"))

        provider = get(space).cryptProviderPtr[0]
        if not provider:
            # Acquire context.
            # This handle is never explicitly released. The operating
            # system will release it when the process terminates.
            if not CryptAcquireContext(
                get(space).cryptProviderPtr, None, None,
                PROV_RSA_FULL, CRYPT_VERIFYCONTEXT):
                raise rwin32.lastWindowsError("CryptAcquireContext")

            provider = get(space).cryptProviderPtr[0]

        # Get random data
        buf = lltype.malloc(rffi.CArray(rwin32.BYTE), n,
                            zero=True, # zero seed
                            flavor='raw')
        try:
            if not CryptGenRandom(provider, n, buf):
                raise rwin32.lastWindowsError("CryptGenRandom")

            return space.wrap(
                rffi.charpsize2str(rffi.cast(rffi.CCHARP, buf), n))
        finally:
            lltype.free(buf, flavor='raw')
