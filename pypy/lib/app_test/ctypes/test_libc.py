import py
import sys, os

from ctypes import *

def setup_module(mod):
    import conftest
    mod.lib = CDLL(str(conftest.sofile))

class TestLibC:
    def test_sqrt(self):
        lib.my_sqrt.argtypes = c_double,
        lib.my_sqrt.restype = c_double
        assert lib.my_sqrt(4.0) == 2.0
        import math
        assert lib.my_sqrt(2.0) == math.sqrt(2.0)

    def test_qsort(self):
        comparefunc = CFUNCTYPE(c_int, POINTER(c_char), POINTER(c_char))
        lib.my_qsort.argtypes = c_void_p, c_size_t, c_size_t, comparefunc
        lib.my_qsort.restype = None

        def sort(a, b):
            return cmp(a[0], b[0])

        chars = create_string_buffer("spam, spam, and spam")
        lib.my_qsort(chars, len(chars)-1, sizeof(c_char), comparefunc(sort))
        assert chars.raw == "   ,,aaaadmmmnpppsss\x00"
