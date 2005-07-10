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
from pypy.rpython.rstr import STR
from pypy.rpython.lltype import malloc


# utility conversion functions
def to_rstr(s):
    p = malloc(STR, len(s))
    for i in range(len(s)):
        p.chars[i] = s[i]
    return p

def from_rstr(rs):
    return ''.join([rs.chars[i] for i in range(len(rs.chars))])

def ll_strcpy(dstchars, srcchars, n):
    i = 0
    while i < n:
        dstchars[i] = srcchars[i]
        i += 1

# ____________________________________________________________

def ll_os_open(fname, flag, mode):
    return os.open(from_rstr(fname), flag, mode)
ll_os_open.suggested_primitive = True


def ll_read_into(fd, buffer):
    data = os.read(fd, len(buffer.chars))
    ll_strcpy(buffer.chars, data, len(data))
    return len(data)
ll_read_into.suggested_primitive = True

def ll_os_read(fd, count):
    if count < 0:
        raise OSError(errno.EINVAL, None)
    buffer = malloc(STR, count)
    n = ll_read_into(fd, buffer)
    if n != count:
        s = malloc(STR, n)
        ll_strcpy(s.chars, buffer.chars, n)
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
