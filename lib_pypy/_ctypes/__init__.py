from _ctypes.dummy import resize
from _ctypes.basics import _CData, sizeof, alignment, byref, addressof,\
     ArgumentError, COMError
from _ctypes.primitive import _SimpleCData
from _ctypes.pointer import _Pointer, _cast_addr
from _ctypes.pointer import POINTER, pointer, _pointer_type_cache
from _ctypes.function import CFuncPtr
from _ctypes.dll import dlopen as LoadLibrary
from _ctypes.structure import Structure
from _ctypes.array import Array
from _ctypes.builtin import _memmove_addr, _string_at, _memset_addr,\
     set_conversion_mode, _wstring_at
from _ctypes.union import Union

import os as _os

if _os.name in ("nt", "ce"):
    from _rawffi import FormatError
    from _rawffi import check_HRESULT as _check_HRESULT
    CopyComPointer = None # XXX

from _rawffi import FUNCFLAG_STDCALL, FUNCFLAG_CDECL, FUNCFLAG_PYTHONAPI
from _rawffi import FUNCFLAG_USE_ERRNO, FUNCFLAG_USE_LASTERROR
from _rawffi import get_errno, set_errno

__version__ = '1.1.0'
#XXX platform dependant?
RTLD_LOCAL = 0
RTLD_GLOBAL = 256
