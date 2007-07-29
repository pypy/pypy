from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.rlib.rarithmetic import intmask
from pypy.rlib import ros
from pypy.interpreter.error import OperationError, wrap_oserror
from pypy.rpython.module.ll_os import RegisterOs

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
lseek.unwrap_spec = [ObjSpace, int, int, int]

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
write.unwrap_spec = [ObjSpace, int, str]

def close(space, fd):
    """Close a file descriptor (for low level IO)."""
    try: 
        os.close(fd)
    except OSError, e: 
        raise wrap_oserror(space, e) 
close.unwrap_spec = [ObjSpace, int]

def ftruncate(space, fd, length):
    """Truncate a file to a specified length."""
    try:
        os.ftruncate(fd, length)
    except OSError, e: 
        raise wrap_oserror(space, e) 
ftruncate.unwrap_spec = [ObjSpace, int, int]

def build_stat_result(space, st):
    # cannot index tuples with a variable...
    lst = [st[0], st[1], st[2], st[3], st[4],
           st[5], st[6], st[7], st[8], st[9]]
    w_tuple = space.newtuple([space.wrap(intmask(x)) for x in lst])
    w_stat_result = space.getattr(space.getbuiltinmodule(os.name),
                                  space.wrap('stat_result'))
    return space.call_function(w_stat_result, w_tuple)

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


# this is a particular case, because we need to supply
# the storage for the environment variables, at least
# for some OSes.

class State:
    def __init__(self, space): 
        self.posix_putenv_garbage = {}
        self.w_environ = space.newdict()
    def startup(self, space):
        _convertenviron(space, self.w_environ)

def get(space): 
    return space.fromcache(State) 

def _convertenviron(space, w_env):
    idx = 0
    while 1:
        s = ros.environ(idx)
        if s is None:
            break
        p = s.find('=')
        if p >= 0:
            key = s[:p]
            value = s[p+1:]
            space.setitem(w_env, space.wrap(key), space.wrap(value))
        idx += 1

def putenv(space, name, value):
    """Change or add an environment variable."""
    txt = '%s=%s' % (name, value)
    ros.putenv(txt)
    # Install the first arg and newstr in posix_putenv_garbage;
    # this will cause previous value to be collected.  This has to
    # happen after the real putenv() call because the old value
    # was still accessible until then.
    get(space).posix_putenv_garbage[name] = txt
putenv.unwrap_spec = [ObjSpace, str, str]

def unsetenv(space, name):
    """Delete an environment variable."""
    if name in get(space).posix_putenv_garbage:
        os.unsetenv(name)
        # Remove the key from posix_putenv_garbage;
        # this will cause it to be collected.  This has to
        # happen after the real unsetenv() call because the
        # old value was still accessible until then.
        del get(space).posix_putenv_garbage[name]
unsetenv.unwrap_spec = [ObjSpace, str]


def enumeratedir(space, dir):
    result = []
    while True:
        nextentry = dir.readdir()
        if nextentry is None:
            break
        if nextentry not in ('.' , '..'):
            result.append(space.wrap(nextentry))
    return space.newlist(result)

def listdir(space, dirname):
    """Return a list containing the names of the entries in the directory.

\tpath: path of directory to list

The list is in arbitrary order.  It does not include the special
entries '.' and '..' even if they are present in the directory."""
    try:
        dir = ros.opendir(dirname)
    except OSError, e: 
        raise wrap_oserror(space, e) 
    try:
        # sub-function call to make sure that 'try:finally:' will catch
        # everything including MemoryErrors
        return enumeratedir(space, dir)
    finally:
        dir.closedir()
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
    try:
        args = [space.str_w(i) for i in space.unpackiterable(w_args)]
        env = {}
        keys = space.call_function(space.getattr(w_env, space.wrap('keys')))
        for key in space.unpackiterable(keys):
            value = space.getitem(w_env, key)
            env[space.str_w(key)] = space.str_w(value)
        os.execve(command, args, env)
    except ValueError, e:
        raise OperationError(space.w_ValueError, space.wrap(str(e)))
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
            ros.utime_null(path)
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
        ros.utime_tuple(path, (actime, modtime))
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
