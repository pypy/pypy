"""
Python interface to the Microsoft Visual C Runtime
Library, providing access to those non-portable, but
still useful routines.
"""

# XXX incomplete: implemented only functions needed by subprocess.py

import _rawffi
import ctypes

_c = ctypes.CDLL('msvcrt', _rawffi.get_libc())

open_osfhandle = _c._open_osfhandle
open_osfhandle.argtypes = [ctypes.c_int, ctypes.c_int]
open_osfhandle.restype = ctypes.c_int

get_osfhandle = _c._get_osfhandle
get_osfhandle.argtypes = [ctypes.c_int]
get_osfhandle.restype = ctypes.c_int

del ctypes
