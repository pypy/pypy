
""" Tests of libffi wrappers and dl* friends
"""

from pypy.rpython.test.test_llinterp import interpret
from pypy.rlib.libffi import *
from pypy.rpython.lltypesystem.ll2ctypes import ALLOCATED
from pypy.rpython.lltypesystem import rffi, lltype
import os, sys
import py

def setup_module(mod):
    if not sys.platform.startswith('linux'):
        py.test.skip("Fragile tests, linux only by now")

class TestDLOperations:
    def setup_method(self, meth):
        ALLOCATED.clear()

    def teardown_method(self, meth):
        pass
        #assert not ALLOCATED, not yet

    def test_dlopen(self):
        py.test.raises(OSError, "dlopen('xxxxxxxxxxxx')")
        assert dlopen('/lib/libc.so.6')
        
    def get_libc(self):
        return CDLL('/lib/libc.so.6')
    
    def test_library_open(self):
        lib = self.get_libc()
        del lib

    def test_library_get_func(self):
        lib = self.get_libc()
        ptr = lib.getpointer('time', [], ffi_type_void)
        py.test.raises(KeyError, lib.getpointer, 'xxxxxxxxxxxxxxx', [], ffi_type_void)
        del lib

    def test_library_func_call(self):
        lib = self.get_libc()
        ptr = lib.getpointer('rand', [], ffi_type_sint)
        zeroes = 0
        for i in range(100):
            res = ptr.call(rffi.INT)
            print res
            if not res:
                zeroes += 1
        assert not zeroes
        # not very hard check, but something :]

    def test_call_args(self):
        libm = CDLL('libm.so')
        pow = libm.getpointer('pow', [ffi_type_double, ffi_type_double],
                              ffi_type_double)
        pow.push_arg(0, 2.0)
        pow.push_arg(1, 2.0)
        res = pow.call(rffi.DOUBLE)
        assert res == 4.0
        pow.push_arg(0, 3.0)
        pow.push_arg(1, 3.0)
        res = pow.call(rffi.DOUBLE)
        assert res == 27.0

    def test_compile(self):
        py.test.skip("Broken")
        def f(x, y):
            libm = CDLL('libm.so')
            c_pow = libm.getpointer('pow', [ffi_type_double, ffi_type_double], ffi_type_double)
            c_pow.push_arg(0, x)
            c_pow.push_arg(1, y)
            return c_pow.call(rffi.DOUBLE)

        interpret(f, [2.0, 4.0])
        
