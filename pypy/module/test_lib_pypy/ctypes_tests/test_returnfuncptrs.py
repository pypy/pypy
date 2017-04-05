import py

from ctypes import *

def setup_module(mod):
    import conftest
    mod.dll = CDLL(str(conftest.sofile))

class TestReturnFuncPtr:

    def test_with_prototype(self):
        # The _ctypes_test shared lib/dll exports quite some functions for testing.
        # The get_strchr function returns a *pointer* to the C strchr function.
        get_strchr = dll.get_strchr
        get_strchr.restype = CFUNCTYPE(c_char_p, c_char_p, c_char)
        strchr = get_strchr()
        assert strchr("abcdef", "b") == "bcdef"
        assert strchr("abcdef", "x") == None
        raises(ArgumentError, strchr, "abcdef", 3)
        raises(TypeError, strchr, "abcdef")

    def test_without_prototype(self):
        get_strchr = dll.get_strchr
        # the default 'c_int' would not work on systems where sizeof(int) != sizeof(void *)
        get_strchr.restype = c_void_p
        addr = get_strchr()
        # _CFuncPtr instances are now callable with an integer argument
        # which denotes a function address:
        strchr = CFUNCTYPE(c_char_p, c_char_p, c_char)(addr)
        assert strchr("abcdef", "b"), "bcdef"
        assert strchr("abcdef", "x") == None
        raises(ArgumentError, strchr, "abcdef", 3)
        raises(TypeError, strchr, "abcdef")
