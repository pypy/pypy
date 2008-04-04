from ctypes import *
import sys, py
from support import BaseCTypesTestChecker

def setup_module(mod):
    import conftest
    mod.lib = CDLL(str(conftest.sofile))

class TestCast(BaseCTypesTestChecker):

    def test_array2pointer(self):
        array = (c_int * 3)(42, 17, 2)

        # casting an array to a pointer works.
        ptr = cast(array, POINTER(c_int))
        assert [ptr[i] for i in range(3)] == [42, 17, 2]

        if 2*sizeof(c_short) == sizeof(c_int):
            ptr = cast(array, POINTER(c_short))
            if sys.byteorder == "little":
                assert [ptr[i] for i in range(6)] == (
                                     [42, 0, 17, 0, 2, 0])
            else:
                assert [ptr[i] for i in range(6)] == (
                                     [0, 42, 0, 17, 0, 2])

    def test_address2pointer(self):
        array = (c_int * 3)(42, 17, 2)

        address = addressof(array)
        ptr = cast(c_void_p(address), POINTER(c_int))
        assert [ptr[i] for i in range(3)] == [42, 17, 2]

        ptr = cast(address, POINTER(c_int))
        assert [ptr[i] for i in range(3)] == [42, 17, 2]

    def test_p2a_objects(self):
        py.test.skip("we make copies of strings")
        array = (c_char_p * 5)()
        assert array._objects is None
        array[0] = "foo bar"
        assert array._objects == {'0': "foo bar"}

        p = cast(array, POINTER(c_char_p))
        # array and p share a common _objects attribute
        assert p._objects is array._objects
        assert array._objects == {'0': "foo bar", id(array): array}
        p[0] = "spam spam"
        assert p._objects == {'0': "spam spam", id(array): array}
        assert array._objects is p._objects
        p[1] = "foo bar"
        assert p._objects == {'1': 'foo bar', '0': "spam spam", id(array): array}
        assert array._objects is p._objects

    def test_other(self):
        p = cast((c_int * 4)(1, 2, 3, 4), POINTER(c_int))
        assert p[:4] == [1,2, 3, 4]
        c_int()
        assert p[:4] == [1, 2, 3, 4]
        p[2] = 96
        assert p[:4] == [1, 2, 96, 4]
        c_int()
        assert p[:4] == [1, 2, 96, 4]

    def test_char_p(self):
        # This didn't work: bad argument to internal function
        s = c_char_p("hiho")
        
        assert cast(cast(s, c_void_p), c_char_p).value == (
                             "hiho")

    try:
        c_wchar_p
    except NameError:
        pass
    else:
        def test_wchar_p(self):
            s = c_wchar_p("hiho")
            assert cast(cast(s, c_void_p), c_wchar_p).value == (
                                 "hiho")

    def test_cast_functype(self):
        # make sure we can cast function type
        my_sqrt = lib.my_sqrt
        sqrt = cast(cast(my_sqrt, c_void_p), CFUNCTYPE(c_double, c_double))
        assert sqrt(4.0) == 2.0
        
