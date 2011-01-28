from ctypes import CDLL, POINTER, pointer, c_byte, c_int
import sys
import py
from support import BaseCTypesTestChecker

class MyCDLL(CDLL):
    def __getattr__(self, attr):
        fn = self[attr] # this way it's not cached as an attribute
        fn._slowpath_allowed = False
        return fn

def setup_module(mod):
    import conftest
    _ctypes_test = str(conftest.sofile)
    mod.dll = MyCDLL(_ctypes_test)


class TestFastpath(BaseCTypesTestChecker):

    def test_fastpath_forbidden(self):
        def errcheck(result, func, args):
            return result
        #
        tf_b = dll.tf_b
        tf_b.restype = c_byte
        tf_b.argtypes = (c_byte,)
        tf_b.errcheck = errcheck # errcheck disables the fastpath
        assert tf_b._is_fastpath
        assert not tf_b._slowpath_allowed
        py.test.raises(AssertionError, "tf_b(-126)")
        del tf_b.errcheck

    def test_simple_args(self):
        tf_b = dll.tf_b
        tf_b.restype = c_byte
        tf_b.argtypes = (c_byte,)
        assert tf_b(-126) == -42

    def test_pointer_args(self):
        f = dll._testfunc_p_p
        f.restype = POINTER(c_int)
        f.argtypes = [POINTER(c_int)]
        v = c_int(42)
        result = f(pointer(v))
        assert type(result) == POINTER(c_int)
        assert result.contents.value == 42
