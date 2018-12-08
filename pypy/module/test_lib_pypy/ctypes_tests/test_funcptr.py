from ctypes import *

class TestCFuncPtr:
    def test_restype(self, dll):
        foo = dll.my_unused_function
        assert foo.restype is c_int     # by default
