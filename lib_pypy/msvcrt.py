"""
Python interface to the Microsoft Visual C Runtime
Library, providing access to those non-portable, but
still useful routines.
"""

# XXX incomplete: implemented only functions needed by subprocess.py
# PAC: 2010/08 added MS locking for Whoosh

import ctypes
from ctypes_support import standard_c_lib as _c
from ctypes_support import get_errno
import errno
import __pypy__

try:
    open_osfhandle = _c._open_osfhandle
except AttributeError: # we are not on windows
    raise ImportError

open_osfhandle.argtypes = [ctypes.c_int, ctypes.c_int]
open_osfhandle.restype = ctypes.c_int

get_osfhandle = _c._get_osfhandle
get_osfhandle.argtypes = [ctypes.c_int]
get_osfhandle.restype = ctypes.c_int

setmode = _c._setmode
setmode.argtypes = [ctypes.c_int, ctypes.c_int]
setmode.restype = ctypes.c_int

LK_UNLCK, LK_LOCK, LK_NBLCK, LK_RLCK, LK_NBRLCK = range(5)

_locking = _c._locking
_locking.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
_locking.restype = ctypes.c_int

@__pypy__.builtinify
def locking(fd, mode, nbytes):
    '''lock or unlock a number of bytes in a file.'''
    rv = _locking(fd, mode, nbytes)
    if rv != 0:
        e = get_errno()
        raise IOError(e, errno.errorcode[e])

del ctypes
