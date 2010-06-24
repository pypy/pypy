"""
Python interface to the Microsoft Visual C Runtime
Library, providing access to those non-portable, but
still useful routines.
"""

# XXX incomplete: implemented only functions needed by subprocess.py

import ctypes
from ctypes_support import standard_c_lib as _c

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

del ctypes
