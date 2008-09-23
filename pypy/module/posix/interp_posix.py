from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.rlib import rposix
from pypy.rlib.rarithmetic import r_longlong
from pypy.rlib.unroll import unrolling_iterable
from pypy.interpreter.error import OperationError, wrap_oserror
from pypy.rpython.module.ll_os import RegisterOs
from pypy.rpython.module import ll_os_stat
from pypy.rpython.lltypesystem import lltype

import os
                          
def open(space, fname, flag, mode=0777):
    """Open a file (for low level IO).
Return a file descriptor (a small integer)."""
    try: 
        fd = os.open(fname, flag, mode)
    except OSError, e: 
        raise wrap_oserror(space, e) 
    return space.wrap(fd)
open.unwrap_spec = [ObjSpace, str, int, int]

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
lseek.unwrap_spec = [ObjSpace, int, r_longlong, int]

def isatty(space, fd):
    """Return True if 'fd' is an open file descriptor connected to the
slave end of a terminal."""
    try:
        res = os.isatty(fd)
    except OSError, e: 
        raise wrap_oserror(space, e) 
    else:  
        return space.wrap(res) 
isatty.unwrap_spec = [ObjSpace, int]

def read(space, fd, buffersize):
    """Read data from a file descriptor."""
    try: 
        s = os.read(fd, buffersize)
    except OSError, e: 
        raise wrap_oserror(space, e) 
    else: 
        return space.wrap(s) 
read.unwrap_spec = [ObjSpace, int, int]

def write(space, fd, data):
    """Write a string to a file descriptor.  Return the number of bytes
actually written, which may be smaller than len(data)."""
    try: 
        res = os.write(fd, data)
    except OSError, e: 
        raise wrap_oserror(space, e) 
    else: 
        return space.wrap(res) 
write.unwrap_spec = [ObjSpace, int, 'bufferstr']

def close(space, fd):
    """Close a file descriptor (for low level IO)."""
    try: 
        os.close(fd)
    except OSError, e: 
        raise wrap_oserror(space, e) 
close.unwrap_spec = [ObjSpace, int]

def closerange(fd_low, fd_high):
    """Closes all file descriptors in [fd_low, fd_high), ignoring errors."""
    rposix.closerange(fd_low, fd_high)
closerange.unwrap_spec = [int, int]

def ftruncate(space, fd, length):
    """Truncate a file to a specified length."""
    try:
        os.ftruncate(fd, length)
    except OSError, e: 
        raise wrap_oserror(space, e) 
ftruncate.unwrap_spec = [ObjSpace, int, r_longlong]

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
    for i, (name, TYPE) in FIELDS:
        value = getattr(st, name)
        #if name in ('st_atime', 'st_mtime', 'st_ctime'):
        #    value = int(value)   # rounded to an integer for indexed access
        w_value = space.wrap(value)
        if i < ll_os_stat.N_INDEXABLE_FIELDS:
            lst[i] = w_value
        else:
            space.setitem(w_keywords, space.wrap(name), w_value)

    # NOTE: float times are disabled for now, for compatibility with CPython
    # non-rounded values for name-based access
    #space.setitem(w_keywords, space.wrap('st_atime'), space.wrap(st.st_atime))
    #space.setitem(w_keywords, space.wrap('st_mtime'), space.wrap(st.st_mtime))
    #space.setitem(w_keywords, space.wrap('st_ctime'), space.wrap(st.st_ctime))

    w_tuple = space.newtuple(lst)
    w_stat_result = space.getattr(space.getbuiltinmodule(os.name),
                                  space.wrap('stat_result'))
    return space.call_function(w_stat_result, w_tuple, w_keywords)

def fstat(space, fd):
    """Perform a stat system call on the file referenced to by an open
file descriptor."""
    try:
        st = os.fstat(fd)
    except OSError, e: 
        raise wrap_oserror(space, e) 
    else:
        return build_stat_result(space, st)
fstat.unwrap_spec = [ObjSpace, int]

def stat(space, path):
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
        st = os.stat(path)
    except OSError, e: 
        raise wrap_oserror(space, e) 
    else: 
        return build_stat_result(space, st)
stat.unwrap_spec = [ObjSpace, str]

def lstat(space, path):
    "Like stat(path), but do no follow symbolic links."
    try:
        st = os.lstat(path)
    except OSError, e:
        raise wrap_oserror(space, e)
    else:
        return build_stat_result(space, st)
lstat.unwrap_spec = [ObjSpace, str]

def dup(space, fd):
    """Create a copy of the file descriptor.  Return the new file
descriptor."""
    try:
        newfd = os.dup(fd)
    except OSError, e: 
        raise wrap_oserror(space, e) 
    else:
        return space.wrap(newfd)
dup.unwrap_spec = [ObjSpace, int]

def dup2(space, old_fd, new_fd):
    """Duplicate a file descriptor."""
    try:
        os.dup2(old_fd, new_fd)
    except OSError, e: 
        raise wrap_oserror(space, e) 
dup2.unwrap_spec = [ObjSpace, int, int]

def access(space, path, mode):
    """
    access(path, mode) -> 1 if granted, 0 otherwise

    Use the real uid/gid to test for access to a path.  Note that most
    operations will use the effective uid/gid, therefore this routine can
    be used in a suid/sgid environment to test if the invoking user has the
    specified access to the path.  The mode argument can be F_OK to test
    existence, or the inclusive-OR of R_OK, W_OK, and X_OK.
    """
    try:
        ok = os.access(path, mode)
    except OSError, e: 
        raise wrap_oserror(space, e) 
    else:
        return space.wrap(ok)
access.unwrap_spec = [ObjSpace, str, int]


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
times.unwrap_spec = [ObjSpace]

def system(space, cmd):
    """Execute the command (a string) in a subshell."""
    try:
        rc = os.system(cmd)
    except OSError, e: 
        raise wrap_oserror(space, e) 
    else: 
        return space.wrap(rc)
system.unwrap_spec = [ObjSpace, str]

def unlink(space, path):
    """Remove a file (same as remove(path))."""
    try:
        os.unlink(path)
    except OSError, e: 
        raise wrap_oserror(space, e) 
unlink.unwrap_spec = [ObjSpace, str]

def remove(space, path):
    """Remove a file (same as unlink(path))."""
    try:
        os.unlink(path)
    except OSError, e: 
        raise wrap_oserror(space, e) 
remove.unwrap_spec = [ObjSpace, str]

def _getfullpathname(space, path):
    """helper for ntpath.abspath """
    posix = __import__(os.name) # nt specific
    try:
        fullpath = posix._getfullpathname(path)
    except OSError, e:
        raise wrap_oserror(space, e) 
    else: 
        return space.wrap(fullpath)
_getfullpathname.unwrap_spec = [ObjSpace, str]

def getcwd(space):
    """Return the current working directory."""
    try:
        cur = os.getcwd()
    except OSError, e: 
        raise wrap_oserror(space, e) 
    else: 
        return space.wrap(cur)
getcwd.unwrap_spec = [ObjSpace]

def chdir(space, path):
    """Change the current working directory to the specified path."""
    try:
        os.chdir(path)
    except OSError, e: 
        raise wrap_oserror(space, e) 
chdir.unwrap_spec = [ObjSpace, str]

def mkdir(space, path, mode=0777):
    """Create a directory."""
    try:
        os.mkdir(path, mode)
    except OSError, e: 
        raise wrap_oserror(space, e) 
mkdir.unwrap_spec = [ObjSpace, str, int]

def rmdir(space, path):
    """Remove a directory."""
    try:
        os.rmdir(path)
    except OSError, e: 
        raise wrap_oserror(space, e) 
rmdir.unwrap_spec = [ObjSpace, str]

def strerror(space, errno):
    """Translate an error code to a message string."""
    try:
        text = os.strerror(errno)
    except ValueError:
        raise OperationError(space.w_ValueError,
                             space.wrap("strerror() argument out of range"))
    return space.wrap(text)
strerror.unwrap_spec = [ObjSpace, int]

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
        space.setitem(w_env, space.wrap(key), space.wrap(value))

def putenv(space, name, value):
    """Change or add an environment variable."""
    try:
        os.environ[name] = value
    except OSError, e:
        raise wrap_oserror(space, e) 
putenv.unwrap_spec = [ObjSpace, str, str]

def unsetenv(space, name):
    """Delete an environment variable."""
    try:
        del os.environ[name]
    except KeyError:
        pass
    except OSError, e:
        raise wrap_oserror(space, e) 
unsetenv.unwrap_spec = [ObjSpace, str]


def listdir(space, dirname):
    """Return a list containing the names of the entries in the directory.

\tpath: path of directory to list

The list is in arbitrary order.  It does not include the special
entries '.' and '..' even if they are present in the directory."""
    try:
        result = os.listdir(dirname)
    except OSError, e:
        raise wrap_oserror(space, e)
    result_w = [space.wrap(s) for s in result]
    return space.newlist(result_w)
listdir.unwrap_spec = [ObjSpace, str]

def pipe(space):
    "Create a pipe.  Returns (read_end, write_end)."
    try: 
        fd1, fd2 = os.pipe()
    except OSError, e: 
        raise wrap_oserror(space, e) 
    return space.newtuple([space.wrap(fd1), space.wrap(fd2)])
pipe.unwrap_spec = [ObjSpace]

def chmod(space, path, mode):
    "Change the access permissions of a file."
    try: 
        os.chmod(path, mode)
    except OSError, e: 
        raise wrap_oserror(space, e) 
chmod.unwrap_spec = [ObjSpace, str, int]

def rename(space, old, new):
    "Rename a file or directory."
    try: 
        os.rename(old, new)
    except OSError, e: 
        raise wrap_oserror(space, e) 
rename.unwrap_spec = [ObjSpace, str, str]

def umask(space, mask):
    "Set the current numeric umask and return the previous umask."
    prevmask = os.umask(mask)
    return space.wrap(prevmask)
umask.unwrap_spec = [ObjSpace, int]

def getpid(space):
    "Return the current process id."
    try: 
        pid = os.getpid()
    except OSError, e: 
        raise wrap_oserror(space, e) 
    return space.wrap(pid)
getpid.unwrap_spec = [ObjSpace]

def kill(space, pid, sig):
    "Kill a process with a signal."
    try:
        os.kill(pid, sig)
    except OSError, e:
        raise wrap_oserror(space, e)
kill.unwrap_spec = [ObjSpace, int, int]

def abort(space):
    """Abort the interpreter immediately.  This 'dumps core' or otherwise fails
in the hardest way possible on the hosting operating system."""
    import signal
    os.kill(os.getpid(), signal.SIGABRT)
abort.unwrap_spec = [ObjSpace]

def link(space, src, dst):
    "Create a hard link to a file."
    try: 
        os.link(src, dst)
    except OSError, e: 
        raise wrap_oserror(space, e) 
link.unwrap_spec = [ObjSpace, str, str]

def symlink(space, src, dst):
    "Create a symbolic link pointing to src named dst."
    try: 
        os.symlink(src, dst)
    except OSError, e: 
        raise wrap_oserror(space, e) 
symlink.unwrap_spec = [ObjSpace, str, str]

def readlink(space, path):
    "Return a string representing the path to which the symbolic link points."
    try:
        result = os.readlink(path)
    except OSError, e: 
        raise wrap_oserror(space, e) 
    return space.wrap(result)
readlink.unwrap_spec = [ObjSpace, str]

def fork(space):
    try:
        pid = os.fork()
    except OSError, e: 
        raise wrap_oserror(space, e) 
    return space.wrap(pid)

def waitpid(space, pid, options):
    try:
        pid, status = os.waitpid(pid, options)
    except OSError, e: 
        raise wrap_oserror(space, e) 
    return space.newtuple([space.wrap(pid), space.wrap(status)])
waitpid.unwrap_spec = [ObjSpace, int, int]

def _exit(space, status):
    os._exit(status)
_exit.unwrap_spec = [ObjSpace, int]

def execv(space, command, w_args):
    """ execv(path, args)

Execute an executable path with arguments, replacing current process.

        path: path of executable file
        args: iterable of strings
    """
    try:
        os.execv(command, [space.str_w(i) for i in space.unpackiterable(w_args)])
    except OperationError, e:
        if not e.match(space, space.w_TypeError):
            raise
        msg = "execv() arg 2 must be an iterable of strings"
        raise OperationError(space.w_TypeError, space.wrap(str(msg)))
    except OSError, e:
        raise wrap_oserror(space, e) 
execv.unwrap_spec = [ObjSpace, str, W_Root]

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
execve.unwrap_spec = [ObjSpace, str, W_Root, W_Root]

def utime(space, path, w_tuple):
    """ utime(path, (atime, mtime))
utime(path, None)

Set the access and modified time of the file to the given values.  If the
second form is used, set the access and modified times to the current time.
    """
    if space.is_w(w_tuple, space.w_None):
        try:
            os.utime(path, None)
            return
        except OSError, e:
            raise wrap_oserror(space, e)
    try:
        msg = "utime() arg 2 must be a tuple (atime, mtime) or None"
        args_w = space.unpackiterable(w_tuple)
        if len(args_w) != 2:
            raise OperationError(space.w_TypeError, space.wrap(msg))
        actime = space.float_w(args_w[0])
        modtime = space.float_w(args_w[1])
        os.utime(path, (actime, modtime))
    except OSError, e:
        raise wrap_oserror(space, e)
    except OperationError, e:
        if not e.match(space, space.w_TypeError):
            raise
        raise OperationError(space.w_TypeError, space.wrap(msg))
utime.unwrap_spec = [ObjSpace, str, W_Root]

def setsid(space):
    """setsid() -> pid
    
    Creates a new session with this process as the leader.
    """
    try:
        result = os.setsid()
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.wrap(result)
setsid.unwrap_spec = [ObjSpace]

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
uname.unwrap_spec = [ObjSpace]

def getuid(space):
    """ getuid() -> uid

    Return the current process's user id.
    """
    return space.wrap(os.getuid())
getuid.unwrap_spec = [ObjSpace]

def setuid(space, arg):
    """ setuid(uid)

    Set the current process's user id.
    """
    try:
        os.setuid(arg)
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.w_None
setuid.unwrap_spec = [ObjSpace, int]

def seteuid(space, arg):
    """ seteuid(uid)

    Set the current process's effective user id.
    """
    try:
        os.seteuid(arg)
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.w_None
seteuid.unwrap_spec = [ObjSpace, int]

def setgid(space, arg):
    """ setgid(gid)

    Set the current process's group id.
    """
    try:
        os.setgid(arg)
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.w_None
setgid.unwrap_spec = [ObjSpace, int]

def setegid(space, arg):
    """ setegid(gid)

    Set the current process's effective group id.
    """
    try:
        os.setegid(arg)
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.w_None
setegid.unwrap_spec = [ObjSpace, int]

def chroot(space, path):
    """ chroot(path)

    Change root directory to path.
    """
    try:
        os.chroot(path)
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.w_None
chroot.unwrap_spec = [ObjSpace, str]

def getgid(space):
    """ getgid() -> gid
    
    Return the current process's group id.
    """
    return space.wrap(os.getgid())
getgid.unwrap_spec = [ObjSpace]

def getegid(space):
    """ getegid() -> gid
    
    Return the current process's effective group id.
    """
    return space.wrap(os.getegid())
getgid.unwrap_spec = [ObjSpace]

def geteuid(space):
    """ geteuid() -> euid

    Return the current process's effective user id.
    """
    return space.wrap(os.geteuid())
geteuid.unwrap_spec = [ObjSpace]

def declare_new_w_star(name):
    if name in RegisterOs.w_star_returning_int:
        def WSTAR(space, status):
            return space.wrap(getattr(os, name)(status))
    else:
        def WSTAR(space, status):
            return space.newbool(getattr(os, name)(status))
    WSTAR.unwrap_spec = [ObjSpace, int]
    WSTAR.func_name = name
    return WSTAR

for name in RegisterOs.w_star:
    func = declare_new_w_star(name)
    globals()[name] = func

def ttyname(space, fd):
    try:
        return space.wrap(os.ttyname(fd))
    except OSError, e:
        raise wrap_oserror(space, e)
ttyname.unwrap_spec = [ObjSpace, int]

def sysconf(space, w_num_or_name):
    # XXX slightly non-nice, reuses the sysconf of the underlying os module
    if space.is_true(space.isinstance(w_num_or_name, space.w_basestring)):
        try:
            num = os.sysconf_names[space.str_w(w_num_or_name)]
        except KeyError:
            raise OperationError(space.w_ValueError,
                                 space.wrap("unrecognized configuration name"))
    else:
        num = space.int_w(w_num_or_name)
    return space.wrap(os.sysconf(num))
sysconf.unwrap_spec = [ObjSpace, W_Root]
