import sys
from pypy.conftest import gettestobjspace
from pypy.rlib.rarithmetic import r_uint
from pypy.module._ffi.interp_ffitype import app_types
from pypy.module._ffi.type_converter import FromAppLevelConverter, ToAppLevelConverter

class DummyFromAppLevelConverter(FromAppLevelConverter):

    def handle_all(self, w_ffitype, w_obj, val):
        self.lastval = val

    handle_signed = handle_all
    handle_unsigned = handle_all
    handle_pointer = handle_all
    handle_char = handle_all        
    handle_unichar = handle_all
    handle_longlong = handle_all
    handle_char_p = handle_all
    handle_unichar_p = handle_all
    handle_float = handle_all
    handle_singlefloat = handle_all
    
    def handle_struct(self, w_ffitype, w_structinstance):
        self.lastval = w_structinstance

    def convert(self, w_ffitype, w_obj):
        self.unwrap_and_do(w_ffitype, w_obj)
        return self.lastval


class TestFromAppLevel(object):

    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('_ffi',))
        converter = DummyFromAppLevelConverter(cls.space)
        cls.from_app_level = staticmethod(converter.convert)

    def check(self, w_ffitype, w_obj, expected):
        v = self.from_app_level(w_ffitype, w_obj)
        assert v == expected
        assert type(v) is type(expected)

    def test_int(self):
        self.check(app_types.sint, self.space.wrap(42), 42)
        self.check(app_types.sint, self.space.wrap(sys.maxint+1), -sys.maxint-1)
        self.check(app_types.sint, self.space.wrap(sys.maxint*2), -2)

    def test_uint(self):
        self.check(app_types.uint, self.space.wrap(42), r_uint(42))
        self.check(app_types.uint, self.space.wrap(-1), r_uint(sys.maxint*2 +1))
        self.check(app_types.uint, self.space.wrap(sys.maxint*3),
                   r_uint(sys.maxint - 2))

    def test_pointer(self):
        # pointers are "unsigned" at applevel, but signed at interp-level (for
        # no good reason, at interp-level Signed or Unsigned makes no
        # difference for passing bits around)
        self.check(app_types.void_p, self.space.wrap(42), 42)
        self.check(
            app_types.void_p, self.space.wrap(sys.maxint+1), -sys.maxint-1)
