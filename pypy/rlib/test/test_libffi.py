
""" Tests of libffi wrappers and dl* friends
"""

from pypy.rpython.test.test_llinterp import interpret
from pypy.rlib.libffi import CDLL, dlopen
from pypy.rpython.lltypesystem.ll2ctypes import ALLOCATED
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
        ptr = lib.getpointer('time')
        py.test.raises(KeyError, lib.getpointer, 'xxxxxxxxxxxxxxx')
        del lib

    def test_library_func_call(self):
        lib = self.get_libc()
        ptr = lib.getpointer('rand')
        zeroes = 0
        for i in range(100):
            res = ptr.call([])
            if not res:
                zeroes += 1
        assert not zeroes
        # not very hard check, but something :]
