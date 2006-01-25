from ctypes import _DLLS
from implementation import RCDLL as CDLL, c_int, c_char_p, c_char, POINTER, \
        RStructure as Structure, RByref as byref
try:
    from implementation import RWinDLL as WinDLL
except ImportError:
    WinDLL = None

cdll = _DLLS(CDLL)
if WinDLL:
    windll = _DLLS(WinDLL)


"""
Loading
-------

windll.LoadLibrary(<somepath>) (<- Windows calling conventions)
cdll.LoadLibrary(<somepath>) (<- Unix calling conventions)

Types
-----

c_char
c_byte
c_ubyte
c_short
c_ushort
c_int
c_uint
c_long
c_ulong
c_longlong
c_ulonglong
c_float
c_double
c_char_p
c_wchar_p
c_void_p

Function Interface
------------------

somefunc.restype = c_char
somefunc.argtypes = [c_char,c_int]

Structure
---------

class POINT(Structure):
    _fields_ = [("x", c_int),
                ("y", c_int)]

Arrays
------

TenPointsArray = POINT * 10
"""
