import py
from ctypes import *
from .support import BaseCTypesTestChecker

ctype_types = [c_byte, c_ubyte, c_short, c_ushort, c_int, c_uint,
                 c_long, c_ulong, c_longlong, c_ulonglong, c_double, c_float]
python_types = [int, int, int, int, int, long,
                int, long, long, long, float, float]

def setup_module(mod):
    import conftest
    mod._ctypes_test = str(conftest.sofile)

class TestPointers(BaseCTypesTestChecker):

    def test_get_ffi_argtype(self):
        P = POINTER(c_int)
        ffitype = P.get_ffi_argtype()
        assert P.get_ffi_argtype() is ffitype
        assert ffitype.deref_pointer() is c_int.get_ffi_argtype()

    def test_byref(self):
        for ct, pt in zip(ctype_types, python_types):
            i = ct(42)
            p = byref(i)
            assert type(p._obj) is ct
            assert p._obj.value == 42

    def test_pointer_to_pointer(self):
        x = c_int(32)
        y = c_int(42)
        p1 = pointer(x)
        p2 = pointer(p1)
        assert p2.contents.contents.value == 32
        p2.contents.contents = y
        assert p2.contents.contents.value == 42
        assert p1.contents.value == 42

    def test_c_char_p_byref(self):
        dll = CDLL(_ctypes_test)
        TwoOutArgs = dll.TwoOutArgs
        TwoOutArgs.restype = None
        TwoOutArgs.argtypes = [c_int, c_void_p, c_int, c_void_p]
        a = c_int(3)
        b = c_int(4)
        c = c_int(5)
        d = c_int(6)
        TwoOutArgs(a, byref(b), c, byref(d))
        assert b.value == 7
        assert d.value == 11

    def test_byref_cannot_be_bound(self):
        class A(object):
            _byref = byref
        A._byref(c_int(5))

    def test_byref_with_offset(self):
        c = c_int()
        d = byref(c)
        base = cast(d, c_void_p).value
        for i in [0, 1, 4, 1444, -10293]:
            assert cast(byref(c, i), c_void_p).value == base + i

    def test_issue2813_fix(self):
        class C(Structure):
            pass
        POINTER(C)
        C._fields_ = [('x', c_int)]
        ffitype = C.get_ffi_argtype()
        assert C.get_ffi_argtype() is ffitype
        assert ffitype.sizeof() == sizeof(c_int)

    def test_issue2813_cant_change_fields_after_get_ffi_argtype(self):
        class C(Structure):
            pass
        ffitype = C.get_ffi_argtype()
        raises(NotImplementedError, "C._fields_ = [('x', c_int)]")
