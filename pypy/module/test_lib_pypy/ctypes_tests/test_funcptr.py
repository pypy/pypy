from ctypes import *

def setup_module(mod):
    import conftest
    _ctypes_test = str(conftest.sofile)
    mod.lib = CDLL(_ctypes_test)


class TestCFuncPtr:
    def test_restype(self):
        foo = lib.my_unused_function
        assert foo.restype is c_int     # by default
