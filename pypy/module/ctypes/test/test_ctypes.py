
from pypy.conftest import gettestobjspace

import os, sys, py

def setup_module(mod):
    if sys.platform != 'linux2':
        py.test.skip("Linux only tests by now")

class AppTestCTypes:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('_ctypes',))

    def test_libload(self):
        import ctypes
        ctypes.CDLL('libc.so.6')

    def test_getattr(self):
        import ctypes
        libc = ctypes.CDLL('libc.so.6')
        func = libc.rand
        assert func.__class__ is libc.__class__._FuncPtr
        assert isinstance(func, ctypes._CFuncPtr)

    def test_rand(self):
        import ctypes
        libc = ctypes.CDLL('libc.so.6')
        first = libc.rand()
        count = 0
        for i in range(100):
            res = libc.rand()
            if res == first:
                count += 1
        assert count != 100
