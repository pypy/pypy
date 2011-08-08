from ctypes import CDLL, POINTER, pointer, c_byte, c_int, c_char_p, CFUNCTYPE, c_void_p, c_size_t
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
    mod.dll = MyCDLL(_ctypes_test)  # slowpath not allowed
    mod.dll2 = CDLL(_ctypes_test)   # slowpath allowed


class TestFastpath(BaseCTypesTestChecker):

    def test_fastpath_forbidden(self):
        def myfunc():
            pass
        #
        tf_b = dll.tf_b
        tf_b.restype = c_byte
        #
        # so far, it's still using the slowpath
        assert not tf_b._is_fastpath
        tf_b.callable = myfunc
        tf_b.argtypes = (c_byte,)
        # errcheck prevented the fastpath to kick in
        assert not tf_b._is_fastpath
        #
        del tf_b.callable
        tf_b.argtypes = (c_byte,) # try to re-enable the fastpath
        assert tf_b._is_fastpath
        #
        assert not tf_b._slowpath_allowed
        py.test.raises(AssertionError, "tf_b.callable = myfunc")
        py.test.raises(AssertionError, "tf_b('aaa')") # force a TypeError

    def test_simple_args(self):
        tf_b = dll.tf_b
        tf_b.restype = c_byte
        tf_b.argtypes = (c_byte,)
        assert tf_b(-126) == -42

    def test_from_cfunctype(self):
        from _ctypes import _memmove_addr
        functype = CFUNCTYPE(c_void_p, c_void_p, c_void_p, c_size_t)
        my_memmove = functype(_memmove_addr)
        assert my_memmove._is_fastpath

    def test_undeclared_restype(self):
        # make sure we get a fresh function
        try:
            del dll.tf_i
        except AttributeError:
            pass
        tf_i = dll.tf_i
        assert not tf_i._is_fastpath
        tf_i.argtypes = (c_int,)
        assert tf_i._is_fastpath
        assert tf_i(12) == 4

    def test_pointer_args(self):
        f = dll._testfunc_p_p
        f.restype = POINTER(c_int)
        f.argtypes = [POINTER(c_int)]
        v = c_int(42)
        result = f(pointer(v))
        assert type(result) == POINTER(c_int)
        assert result.contents.value == 42

    def test_simple_pointer_args(self):
        f = dll.my_strchr
        f.argtypes = [c_char_p, c_int]
        f.restype = c_char_p
        mystr = c_char_p("abcd")
        result = f(mystr, ord("b"))
        assert result == "bcd"

    def test_strings(self):
        f = dll.my_strchr
        f.argtypes = [c_char_p, c_int]
        f.restype = c_char_p
        result = f("abcd", ord("b"))
        assert result == "bcd"

    def test_errcheck(self):
        def errcheck(result, func, args):
            return 'hello'
        tf_b = dll.tf_b
        tf_b.restype = c_byte
        tf_b.argtypes = (c_byte,)
        tf_b.errcheck = errcheck
        assert tf_b(-126) == 'hello'


class TestFallbackToSlowpath(BaseCTypesTestChecker):

    def test_argtypes_is_None(self):
        tf_b = dll2.tf_b
        tf_b.restype = c_byte
        tf_b.argtypes = (c_char_p,)  # this is intentionally wrong
        tf_b.argtypes = None # kill the fast path
        assert not tf_b._is_fastpath
        assert tf_b(-126) == -42

    def test_callable_is_None(self):
        tf_b = dll2.tf_b
        tf_b.restype = c_byte
        tf_b.argtypes = (c_byte,)
        tf_b.callable = lambda x: x+1
        assert not tf_b._is_fastpath
        assert tf_b(-126) == -125
        tf_b.callable = None
