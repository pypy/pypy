"""
Dummy low-level implementations for the external functions of the 'os' module.
"""

# Idea: each ll_os_xxx() function calls back the os.xxx() function that it
# is supposed to implement, either directly or indirectly if there is some
# argument decoding and buffering preparation that can be done here.

# The specific function that calls back to os.xxx() is tagged with the
# 'suggested_primitive' flag.  The back-end should special-case it and really
# implement it.  The back-end can actually choose to special-case any function:
# it can for example special-case ll_os_xxx() directly even if the
# 'suggested_primitive' flag is set to another function, if the conversion
# and buffer preparation stuff is not useful.

import os, errno
from pypy.rpython.lltypesystem.lltype import \
     GcStruct, Signed, Array, Char, Ptr, malloc
from pypy.rpython.module.support import to_rstr, from_rstr, ll_strcpy, _ll_strfill
from pypy.rpython.module.support import to_opaque_object, from_opaque_object
from pypy.rpython import ros
from pypy.rpython.rarithmetic import r_longlong

def ll_os_open(fname, flag, mode):
    return os.open(from_rstr(fname), flag, mode)
ll_os_open.suggested_primitive = True


def ll_read_into(fd, buffer):
    data = os.read(fd, len(buffer.chars))
    _ll_strfill(buffer, data, len(data))
    return len(data)
ll_read_into.suggested_primitive = True

def ll_os_read(fd, count):
    from pypy.rpython.lltypesystem.rstr import STR
    if count < 0:
        raise OSError(errno.EINVAL, None)
    buffer = malloc(STR, count)
    n = ll_read_into(fd, buffer)
    if n != count:
        s = malloc(STR, n)
        ll_strcpy(s, buffer, n)
        buffer = s
    return buffer


def ll_os_write(fd, astring):
    return os.write(fd, from_rstr(astring))
ll_os_write.suggested_primitive = True


def ll_os_close(fd):
    os.close(fd)
ll_os_close.suggested_primitive = True


def ll_os_getcwd():
    return to_rstr(os.getcwd())
ll_os_getcwd.suggested_primitive = True


def ll_os_dup(fd):
    return os.dup(fd)
ll_os_dup.suggested_primitive = True

def ll_os_lseek(fd,pos,how):
    return r_longlong(os.lseek(fd,pos,how))
ll_os_lseek.suggested_primitive = True

def ll_os_isatty(fd):
    return os.isatty(fd)
ll_os_isatty.suggested_primitive = True

def ll_os_ftruncate(fd,len):
    return os.ftruncate(fd,len)
ll_os_ftruncate.suggested_primitive = True

n = 10
fieldnames = ['item%d' % i for i in range(n)]
lltypes = [Signed]*n
fields = tuple(zip(fieldnames, lltypes))    
STAT_RESULT = GcStruct('tuple%d' % n, *fields)

from pypy.rpython.rarithmetic import intmask

def ll_stat_result(stat0, stat1, stat2, stat3, stat4,
                   stat5, stat6, stat7, stat8, stat9):
    tup = malloc(STAT_RESULT)
    tup.item0 = intmask(stat0)
    tup.item1 = intmask(stat1)
    tup.item2 = intmask(stat2)
    tup.item3 = intmask(stat3)
    tup.item4 = intmask(stat4)
    tup.item5 = intmask(stat5)
    tup.item6 = intmask(stat6)
    tup.item7 = intmask(stat7)
    tup.item8 = intmask(stat8)
    tup.item9 = intmask(stat9)
    return tup
    
def ll_os_fstat(fd):
    (stat0, stat1, stat2, stat3, stat4,
     stat5, stat6, stat7, stat8, stat9) = os.fstat(fd)
    return ll_stat_result(stat0, stat1, stat2, stat3, stat4,
                          stat5, stat6, stat7, stat8, stat9)
ll_os_fstat.suggested_primitive = True

def ll_os_stat(path):
    (stat0, stat1, stat2, stat3, stat4,
     stat5, stat6, stat7, stat8, stat9) = os.stat(from_rstr(path))
    return ll_stat_result(stat0, stat1, stat2, stat3, stat4,
                          stat5, stat6, stat7, stat8, stat9)
ll_os_stat.suggested_primitive = True

def ll_os_strerror(errnum):
    return to_rstr(os.strerror(errnum))
ll_os_strerror.suggested_primitive = True

def ll_os_system(cmd):
    return os.system(from_rstr(cmd))
ll_os_system.suggested_primitive = True

def ll_os_unlink(path):
    os.unlink(from_rstr(path))
ll_os_unlink.suggested_primitive = True

def ll_os_chdir(path):
    os.chdir(from_rstr(path))
ll_os_chdir.suggested_primitive = True

def ll_os_mkdir(path, mode):
    os.mkdir(from_rstr(path), mode)
ll_os_mkdir.suggested_primitive = True

def ll_os_rmdir(path):
    os.rmdir(from_rstr(path))
ll_os_rmdir.suggested_primitive = True

# this function is not really the os thing, but the internal one.
def ll_os_putenv(name_eq_value):
    ros.putenv(from_rstr(name_eq_value))
ll_os_putenv.suggested_primitive = True

def ll_os_unsetenv(name):
    os.unsetenv(from_rstr(name))
ll_os_unsetenv.suggested_primitive = True

# get the initial environment by indexing
def ll_os_environ(idx):
    return ros.environ(idx)
ll_os_environ.suggested_primitive = True

# ____________________________________________________________
# opendir/readdir

def ll_os_opendir(dirname):
    dir = ros.opendir(from_rstr(dirname))
    return to_opaque_object(dir)
ll_os_opendir.suggested_primitive = True

def ll_os_readdir(opaquedir):
    dir = from_opaque_object(opaquedir)
    nextentry = dir.readdir()
    return to_rstr(nextentry)
ll_os_readdir.suggested_primitive = True

def ll_os_closedir(opaquedir):
    dir = from_opaque_object(opaquedir)
    dir.closedir()
ll_os_closedir.suggested_primitive = True
