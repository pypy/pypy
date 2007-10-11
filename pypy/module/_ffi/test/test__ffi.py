

from pypy.conftest import gettestobjspace

import os, sys, py

def setup_module(mod):
    if sys.platform != 'linux2':
        py.test.skip("Linux only tests by now")

class AppTestCTypes:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('_ffi',))

    def test_libload(self):
        import _ffi
        _ffi.CDLL('libc.so.6')

    def test_getattr(self):
        import _ffi
        libc = _ffi.CDLL('libc.so.6')
        func = libc.ptr('rand', [], 'i')
        assert libc.ptr('rand', [], 'i') is func # caching
        assert libc.ptr('rand', [], 'l') is not func
        assert isinstance(func, _ffi.FuncPtr)
        raises(AttributeError, "libc.xxxxxxxxxxxxxx")

    def test_rand(self):
        import _ffi
        libc = _ffi.CDLL('libc.so.6')
        func = libc.ptr('rand', [], 'i')
        first = func()
        count = 0
        for i in range(100):
            res = func()
            if res == first:
                count += 1
        assert count != 100

    def test_pow(self):
        import _ffi
        libm = _ffi.CDLL('libm.so')
        pow = libm.ptr('pow', ['d', 'd'], 'd')
        assert pow(2.0, 2.0) == 4.0
        assert pow(3.0, 3.0) == 27.0
        assert pow(2, 2) == 4.0
        raises(TypeError, "pow('x', 2.0)")

        
