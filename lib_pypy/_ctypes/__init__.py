from _ctypes.dummy import resize
from _ctypes.basics import _CData, sizeof, alignment, byref, addressof,\
     ArgumentError, COMError
from _ctypes.primitive import _SimpleCData
from _ctypes.pointer import _Pointer, _cast_addr
from _ctypes.pointer import POINTER, pointer, _pointer_type_cache
from _ctypes.function import CFuncPtr, call_function
from _ctypes.dll import dlopen
from _ctypes.structure import Structure
from _ctypes.array import Array
from _ctypes.builtin import (
    _memmove_addr, _memset_addr,
    _string_at_addr, _wstring_at_addr, set_conversion_mode)
from _ctypes.union import Union

import os as _os

if _os.name in ("nt", "ce"):
    from _rawffi import FormatError
    from _rawffi import check_HRESULT as _check_HRESULT
    CopyComPointer = None # XXX
    LoadLibrary = dlopen

from _rawffi import FUNCFLAG_STDCALL, FUNCFLAG_CDECL, FUNCFLAG_PYTHONAPI
from _rawffi import FUNCFLAG_USE_ERRNO, FUNCFLAG_USE_LASTERROR

from _ctypes.builtin import get_errno, set_errno
if _os.name in ("nt", "ce"):
    from _ctypes.builtin import get_last_error, set_last_error

__version__ = '1.1.0'
#XXX platform dependant?
RTLD_LOCAL = 0
RTLD_GLOBAL = 256
