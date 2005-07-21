from pypy.interpreter.baseobjspace import ObjSpace

import os
from os import *

def open(space, w_fname, w_flag, w_mode=0777):
    fname = space.str_w(w_fname)
    flag = space.int_w(w_flag)
    mode = space.int_w(w_mode)
    # notice that an unwrap_spec attached to open could be used to the same effect
    fd = os.open(fname, flag, mode)
    return space.wrap(fd)


def lseek(space, fd, pos, how):
    os.lseek(fd,pos,how)
lseek.unwrap_spec = [ObjSpace, int, int, int]

def isatty(space, fd):
    return os.isatty(w_fd)
isatty.unwrap_spec = [ObjSpace, int]

def read(space, fd, buffersize):
    return os.read(fd,buffersize)
read.unwrap_spec = [ObjSpace, int, int]

def write(space, fd, data):
    return os.write( fd, data)
write.unwrap_spec = [ObjSpace, int, str]

def close(space, fd):
    os.close(fd)
close.unwrap_spec = [ObjSpace, int]

def ftruncate(space, fd, length):
    os.ftruncate(fd, length)
ftruncate.unwrap_spec = [ObjSpace, int, int]

def fstat(space, fd):
    return os.fstat(fd)
fstat.unwrap_spec = [ObjSpace, int]

def stat(space, path):
    return os.stat(path)
stat.unwrap_spec = [ObjSpace, str]

def getcwd(space):
    return os.getcwd()
getcwd.unwrap_spec = [ObjSpace]

def dup(space, fd):
    return os.dup(fd)
dup.unwrap_spec = [ObjSpace, int]