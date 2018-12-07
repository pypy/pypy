import pytest
from ctypes import *
from .support import BaseCTypesTestChecker
import sys, struct

def valid_ranges(*types):
    # given a sequence of numeric types, collect their _type_
    # attribute, which is a single format character compatible with
    # the struct module, use the struct module to calculate the
    # minimum and maximum value allowed for this format.
    # Returns a list of (min, max) values.
    result = []
    for t in types:
        fmt = t._type_
        size = struct.calcsize(fmt)
        a = struct.unpack(fmt, ("\x00"*32)[:size])[0]
        b = struct.unpack(fmt, ("\xFF"*32)[:size])[0]
        c = struct.unpack(fmt, ("\x7F"+"\x00"*32)[:size])[0]
        d = struct.unpack(fmt, ("\x80"+"\xFF"*32)[:size])[0]
        result.append((min(a, b, c, d), max(a, b, c, d)))
    return result

ArgType = type(byref(c_int(0)))

unsigned_types = [c_ubyte, c_ushort, c_uint, c_ulong]
signed_types = [c_byte, c_short, c_int, c_long, c_longlong]

float_types = [c_double, c_float, c_longdouble]

try:
    c_ulonglong
    c_longlong
except NameError:
    pass
else:
    unsigned_types.append(c_ulonglong)
    signed_types.append(c_longlong)

unsigned_ranges = valid_ranges(*unsigned_types)
signed_ranges = valid_ranges(*signed_types)

################################################################

class TestNumber(BaseCTypesTestChecker):

    def test_init_again(self):
        for t in signed_types + unsigned_types + float_types:
            parm = t()
            addr1 = addressof(parm)
            parm.__init__(0)
            addr2 = addressof(parm)
            assert addr1 == addr2

    def test_subclass(self):
        class enum(c_int):
            def __new__(cls, value):
                dont_call_me
        class S(Structure):
            _fields_ = [('t', enum)]
        assert isinstance(S().t, enum)

    #@pytest.mark.xfail("'__pypy__' not in sys.builtin_module_names")
    @pytest.mark.xfail
    def test_no_missing_shape_to_ffi_type(self):
        # whitebox test
        "re-enable after adding 'g' to _shape_to_ffi_type.typemap, "
        "which I think needs fighting all the way up from "
        "rpython.rlib.libffi"
        from _ctypes.basics import _shape_to_ffi_type
        from _rawffi import Array
        for i in range(1, 256):
            try:
                Array(chr(i))
            except ValueError:
                pass
            else:
                assert chr(i) in _shape_to_ffi_type.typemap

    @pytest.mark.xfail
    def test_pointer_to_long_double(self):
        import ctypes
        ctypes.POINTER(ctypes.c_longdouble)
