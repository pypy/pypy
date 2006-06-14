from pypy.interpreter.baseobjspace import ObjSpace
from pypy.rpython.rarithmetic import intmask
from pypy.rpython import ros
from pypy.interpreter.error import OperationError

import os
from os import *

def wrap_oserror(space, e): 
    assert isinstance(e, OSError) 
    errno = e.errno
    try:
        msg = os.strerror(errno)
    except ValueError:
        msg = 'error %d' % errno
    w_error = space.call_function(space.w_OSError,
                                  space.wrap(errno),
                                  space.wrap(msg))
    return OperationError(space.w_OSError, w_error)
                          
def open(space, fname, flag, mode=0777):
    try: 
        fd = os.open(fname, flag, mode)
    except OSError, e: 
        raise wrap_oserror(space, e) 
    return space.wrap(fd)
open.unwrap_spec = [ObjSpace, str, int, int]

def lseek(space, fd, pos, how):
    try:
        pos = os.lseek(fd, pos, how)
    except OSError, e: 
        raise wrap_oserror(space, e) 
    else: 
        return space.wrap(pos) 
lseek.unwrap_spec = [ObjSpace, int, int, int]

def isatty(space, fd):
    try:
        res = os.isatty(fd)
    except OSError, e: 
        raise wrap_oserror(space, e) 
    else:  
        return space.wrap(res) 
isatty.unwrap_spec = [ObjSpace, int]

def read(space, fd, buffersize):
    try: 
        s = os.read(fd, buffersize)
    except OSError, e: 
        raise wrap_oserror(space, e) 
    else: 
        return space.wrap(s) 
read.unwrap_spec = [ObjSpace, int, int]

def write(space, fd, data):
    try: 
        res = os.write(fd, data)
    except OSError, e: 
        raise wrap_oserror(space, e) 
    else: 
        return space.wrap(res) 
write.unwrap_spec = [ObjSpace, int, str]

def close(space, fd):
    try: 
        os.close(fd)
    except OSError, e: 
        raise wrap_oserror(space, e) 
close.unwrap_spec = [ObjSpace, int]

def ftruncate(space, fd, length):
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
    try:
        st = os.fstat(fd)
    except OSError, e: 
        raise wrap_oserror(space, e) 
    else:
        return build_stat_result(space, st)
fstat.unwrap_spec = [ObjSpace, int]

def stat(space, path):
    try:
        st = os.stat(path)
    except OSError, e: 
        raise wrap_oserror(space, e) 
    else: 
        return build_stat_result(space, st)
stat.unwrap_spec = [ObjSpace, str]

def dup(space, fd):
    try:
        newfd = os.dup(fd)
    except OSError, e: 
        raise wrap_oserror(space, e) 
    else:
        return space.wrap(newfd)
dup.unwrap_spec = [ObjSpace, int]

def system(space, cmd):
    """system(command) -> exit_status

Execute the command (a string) in a subshell."""
    try:
        rc = os.system(cmd)
    except OSError, e: 
        raise wrap_oserror(space, e) 
    else: 
        return space.wrap(rc)
system.unwrap_spec = [ObjSpace, str]

def unlink(space, path):
    """unlink(path)

Remove a file (same as remove(path))."""
    try:
        os.unlink(path)
    except OSError, e: 
        raise wrap_oserror(space, e) 
unlink.unwrap_spec = [ObjSpace, str]

def remove(space, path):
    """remove(path)

Remove a file (same as unlink(path))."""
    try:
        os.unlink(path)
    except OSError, e: 
        raise wrap_oserror(space, e) 
remove.unwrap_spec = [ObjSpace, str]

def getcwd(space):
    try:
        cur = os.getcwd()
    except OSError, e: 
        raise wrap_oserror(space, e) 
    else: 
        return space.wrap(cur)
getcwd.unwrap_spec = [ObjSpace]

def chdir(space, path):
    """chdir(path)

Change the current working directory to the specified path."""
    try:
        os.chdir(path)
    except OSError, e: 
        raise wrap_oserror(space, e) 
chdir.unwrap_spec = [ObjSpace, str]

def mkdir(space, path, mode=0777):
    """mkdir(path [, mode=0777])

Create a directory."""
    try:
        os.mkdir(path, mode)
    except OSError, e: 
        raise wrap_oserror(space, e) 
mkdir.unwrap_spec = [ObjSpace, str, int]

def rmdir(space, path):
    """rmdir(path)

Remove a directory."""
    try:
        os.rmdir(path)
    except OSError, e: 
        raise wrap_oserror(space, e) 
rmdir.unwrap_spec = [ObjSpace, str]

def strerror(space, errno):
    'strerror(code) -> string\n\nTranslate an error code to a message string.'
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
        self.w_environ = space.newdict([])
        _convertenviron(space, self.w_environ)
def get(space): 
    return space.fromcache(State) 

def _convertenviron(space, w_env):
    idx = 0
    while 1:
        s = ros.environ(idx)
        if s is None:
            break
        p = s.find('=');
        if p >= 0:
            assert p >= 0
            key = s[:p]
            value = s[p+1:]
            space.setitem(w_env, space.wrap(key), space.wrap(value))
        idx += 1

def putenv(space, name, value):
    """putenv(key, value)

Change or add an environment variable."""
    txt = '%s=%s' % (name, value)
    ros.putenv(txt)
    # Install the first arg and newstr in posix_putenv_garbage;
    # this will cause previous value to be collected.  This has to
    # happen after the real putenv() call because the old value
    # was still accessible until then.
    get(space).posix_putenv_garbage[name] = txt
putenv.unwrap_spec = [ObjSpace, str, str]

def unsetenv(space, name):
    """unsetenv(key)

Delete an environment variable."""
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
    """listdir(path) -> list_of_strings

Return a list containing the names of the entries in the directory.

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
