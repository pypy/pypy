
import ctypes
from pypy.rpython.tool.mkrffi import *
from pypy.rpython.tool.test.test_c import TestBasic
import py

class TestMkrffi(TestBasic):
    def test_single_func(self):
        func = self.lib.int_to_void_p
        func.argtypes = [ctypes.c_int]
        func.restype = ctypes.c_voidp

        src = proc_func(func)
        _src = py.code.Source("""
        c_int_to_void_p = rffi.llexternal('int_to_void_p', [rffi.INT], lltype.Ptr(lltype.FixedSizeArray(lltype.Void, 1)))
        """)

        assert src == _src, str(src) + "\n" + str(_src)
