import py
from support import BaseCTypesTestChecker
from ctypes import *


subclasses = []
for base in [c_byte, c_short, c_int, c_long, c_longlong,
        c_ubyte, c_ushort, c_uint, c_ulong, c_ulonglong,
        c_float, c_double]:
    class X(base):
        pass
    subclasses.append(X)

class X(c_char):
    pass

# This test checks if the __repr__ is correct for subclasses of simple types

class TestRepr(BaseCTypesTestChecker):
    def test_numbers(self):
        py.test.skip("reprs not implemented")
        for typ in subclasses:
            base = typ.__bases__[0]
            assert repr(base(42)).startswith(base.__name__)
            assert "<X object at" == repr(typ(42))[:12]

    def test_char(self):
        py.test.skip("reprs not implemented")
        assert "c_char('x')" == repr(c_char('x'))
        assert "<X object at" == repr(X('x'))[:12]
