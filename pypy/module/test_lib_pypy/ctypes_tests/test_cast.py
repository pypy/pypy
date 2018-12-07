from ctypes import *
import sys, py
from .support import BaseCTypesTestChecker

def setup_module(mod):
    import conftest
    mod.lib = CDLL(str(conftest.sofile))

class TestCast(BaseCTypesTestChecker):

    def test_cast_functype(self):
        # make sure we can cast function type
        my_sqrt = lib.my_sqrt
        saved_objects = my_sqrt._objects.copy()
        sqrt = cast(cast(my_sqrt, c_void_p), CFUNCTYPE(c_double, c_double))
        assert sqrt(4.0) == 2.0
        assert not cast(0, CFUNCTYPE(c_int))
        #
        assert sqrt._objects is my_sqrt._objects   # on CPython too
        my_sqrt._objects.clear()
        my_sqrt._objects.update(saved_objects)

    def test_cast_argumenterror(self):
        param = c_uint(42)
        py.test.raises(ArgumentError, "cast(param, c_void_p)")

    def test_c_bool(self):
        x = c_bool(42)
        assert x.value is True
        x = c_bool(0.0)
        assert x.value is False
        x = c_bool("")
        assert x.value is False
        x = c_bool(['yadda'])
        assert x.value is True
