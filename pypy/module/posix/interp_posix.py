from pypy.interpreter.baseobjspace import ObjSpace
from pypy.rpython.rarithmetic import intmask

import os
from os import *

def open(space, fname, flag, mode=0777):
    fd = os.open(fname, flag, mode)
    return space.wrap(fd)
open.unwrap_spec = [ObjSpace, str, int, int]

def lseek(space, fd, pos, how):
    return space.wrap(os.lseek(fd, pos, how))
lseek.unwrap_spec = [ObjSpace, int, int, int]

def isatty(space, fd):
    return space.wrap(os.isatty(fd))
isatty.unwrap_spec = [ObjSpace, int]

def read(space, fd, buffersize):
    return space.wrap(os.read(fd, buffersize))
read.unwrap_spec = [ObjSpace, int, int]

def write(space, fd, data):
    return space.wrap(os.write(fd, data))
write.unwrap_spec = [ObjSpace, int, str]

def close(space, fd):
    os.close(fd)
close.unwrap_spec = [ObjSpace, int]

def ftruncate(space, fd, length):
    os.ftruncate(fd, length)
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
    return build_stat_result(space, os.fstat(fd))
fstat.unwrap_spec = [ObjSpace, int]

def stat(space, path):
    return build_stat_result(space, os.stat(path))
stat.unwrap_spec = [ObjSpace, str]

def getcwd(space):
    return space.wrap(os.getcwd())
getcwd.unwrap_spec = [ObjSpace]

def dup(space, fd):
    return space.wrap(os.dup(fd))
dup.unwrap_spec = [ObjSpace, int]
