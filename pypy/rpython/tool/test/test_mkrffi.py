
import ctypes
from pypy.rpython.tool.mkrffi import *

def test_func():

    lib = ctypes.CDLL('libc.so.6')
    func = lib.malloc
    func.argtypes = [ctypes.c_int]
    func.restype = ctypes.c_voidp

    src = proc_func(func)
    assert isinstance(src, Source)
    _src = Source("""
    c_malloc = rffi.llexternal('malloc', [rffi.INT], 
          lltype.Ptr(lltype.FixedSizeArray(lltype.Void, 1)))
    """)

    assert src == _src
