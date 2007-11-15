
from pypy.conftest import gettestobjspace
import sys, py
from pypy.module._ffi.test.test__ffi import AppTestFfi as BaseTestFfi

def setup_module(mod):
    if sys.platform != 'linux2':
        py.test.skip("Linux only tests by now")

class AppTestCtypes(BaseTestFfi):
    def test_libload(self):
        import ctypes
        ctypes.CDLL('libc.so.6')

    def test_getattr(self):
        import ctypes
        libc = ctypes.CDLL('libc.so.6')
        rand = libc.rand
        rand.restype = ctypes.c_int
        assert libc.rand is rand
        assert libc['rand'] is not rand
        assert isinstance(rand, ctypes._CFuncPtr)
        raises(AttributeError, 'libc.xxxxxxxxxxxxxxxx')

    def test_short_addition(self):
        import ctypes
        lib = ctypes.CDLL(self.lib_name)
        short_add = lib.add_shorts
        short_add.argtypes = [ctypes.c_short, ctypes.c_short]
        short_add.restype = ctypes.c_ushort
        assert short_add(1, 2) == 3

    def test_rand(self):
        import ctypes
        libc = ctypes.CDLL('libc.so.6')
        func = libc.rand
        first = func()
        count = 0
        for i in range(100):
            res = func()
            if res == first:
                count += 1
        assert count != 100

    def test_pow(self):
        import ctypes
        libm = ctypes.CDLL('libm.so')
        pow = libm.pow
        pow.argtypes = [ctypes.c_double, ctypes.c_double]
        pow.restype = ctypes.c_double
        assert pow(2.0, 2.0) == 4.0
        assert pow(3.0, 3.0) == 27.0
        assert pow(2, 2) == 4.0
        raises(ctypes.ArgumentError, "pow('x', 2.0)")

    def not_implemented(self):
        skip("not implemented")

    test_getchar = not_implemented
    test_returning_str = not_implemented
    test_strlen = not_implemented
    test_time = not_implemented
    test_gettimeofday = not_implemented
    test_structreturn = not_implemented
    test_nested_structures = not_implemented
    test_array = not_implemented
    test_array_of_structure = not_implemented
    test_bad_parameters = not_implemented
    test_implicit_structure = not_implemented
    test_longs_ulongs = not_implemented
    test_callback = not_implemented
