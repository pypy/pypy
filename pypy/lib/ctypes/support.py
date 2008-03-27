
""" This file provides some support for things like standard_c_lib and
errno access, as portable as possible
"""

import ctypes
import ctypes.util
import sys

# __________ the standard C library __________

if sys.platform == 'win32':
    # trying to guess the correct libc... only a few tests fail if there
    # is a mismatch between the one used by python2x.dll and the one
    # loaded here
    if sys.version_info < (2, 4):
        standard_c_lib = ctypes.cdll.LoadLibrary('msvcrt.dll')
    else:
        standard_c_lib = ctypes.cdll.LoadLibrary('msvcr71.dll')
else:
    standard_c_lib = ctypes.cdll.LoadLibrary(ctypes.util.find_library('c'))

if sys.platform == 'win32':
    standard_c_lib._errno.restype = ctypes.POINTER(ctypes.c_int)
    def _where_is_errno():
        return standard_c_lib._errno()
    
elif sys.platform in ('linux2', 'freebsd6'):
    standard_c_lib.__errno_location.restype = ctypes.POINTER(ctypes.c_int)
    def _where_is_errno():
        return standard_c_lib.__errno_location()

elif sys.platform == 'darwin':
    standard_c_lib.__error.restype = ctypes.POINTER(ctypes.c_int)
    def _where_is_errno():
        return standard_c_lib.__error()

def get_errno():
    errno_p = _where_is_errno()
    return errno_p.contents.value

def set_errno(value):
    errno_p = _where_is_errno()
    errno_p.contents.value = value


