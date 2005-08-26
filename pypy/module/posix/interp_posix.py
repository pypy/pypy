from pypy.interpreter.baseobjspace import ObjSpace
from pypy.rpython.rarithmetic import intmask
from pypy.interpreter.error import OperationError

import os
from os import *

def wrap_oserror(space, e): 
    assert isinstance(e, OSError) 
    errno = e.errno 
    msg = os.strerror(errno) 
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
    w_stat_result = space.getattr(space.getbuiltinmodule('posix'),
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
