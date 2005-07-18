from pypy.interpreter.baseobjspace import ObjSpace,W_Root

import os
from os import *

def open(space, w_fname, w_flag, w_mode=0777):
    fname = space.str_w(w_fname)
    flag = space.int_w(w_flag)
    mode = space.int_w(w_mode)
    # notice that an unwrap_spec attached to open could be used to the same effect
    fd = os.open(fname, flag, mode)
    return space.wrap(fd)


def lseek(space, w_fd, pos, how):
    os.lseek(fd,pos,how)
lseek.unwrap_spec = [ObjSpace, W_Root, int, int]

def isatty(space, w_fd):
    return os.isatty(fd)
lseek.unwrap_spec = [ObjSpace, W_Root, int, int]

def read(space, w_fd, buffersize):
    return os.read(w_fd,buffersize)
read.unwrap_spec = [ObjSpace, W_Root, int]

def write(space, w_fd, data):
    return os.write( w_fd, data)
write.unwrap_spec = [ObjSpace, W_Root, str]

def close(space, w_fd):
    os.close(w_fd)
close.unwrap_spec = [ObjSpace, W_Root]

def ftruncate(space, w_fd, length):
    os.ftruncate(w_fd, length)
ftruncate.unwrap_spec = [ObjSpace, W_Root, int]

def fstat(space, w_fd):
    return os.fstat(w_fd)
fstat.unwrap_spec = [ObjSpace, W_Root]

def getcwd(space):
    return os.getcwd()
getcwd.unwrap_spec = [ObjSpace]

def dup(space, w_fd):
    return os.dup(w_fd)
dup.unwrap_spec = [ObjSpace, W_Root]