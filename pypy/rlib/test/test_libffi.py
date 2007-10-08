
""" Tests of libffi wrappers and dl* friends
"""

from pypy.rpython.test.test_llinterp import interpret
from pypy.rlib.libffi import CDLL, dlopen
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
        ptr = lib.getpointer('time', [], lltype.Void)
        py.test.raises(KeyError, lib.getpointer, 'xxxxxxxxxxxxxxx', [], lltype.Void)
        del lib

    def test_library_func_call(self):
        lib = self.get_libc()
        ptr = lib.getpointer('rand', [], rffi.INT)
        zeroes = 0
        for i in range(100):
            res = ptr.call([])
            if not res:
                zeroes += 1
        assert not zeroes
        # not very hard check, but something :]

    def test_call_args(self):
        libm = CDLL('libm.so')
        pow = libm.getpointer('pow', [rffi.DOUBLE, rffi.DOUBLE], rffi.DOUBLE)
        assert pow.call((2.0, 2.0)) == 4.0
        assert pow.call((3.0, 3.0)) == 27.0

    def test_compile(self):
        py.test.skip("in-progress")
        def f(x, y):
            libm = CDLL('libm.so')
            c_pow = libm.getpointer('pow', (rffi.DOUBLE, rffi.DOUBLE), rffi.DOUBLE)
            return c_pow.call((x, y))

        interpret(f, [2.0, 4.0])
