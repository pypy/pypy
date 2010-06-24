import py
from support import BaseCTypesTestChecker
from ctypes import *

def setup_module(mod):
    import conftest
    _ctypes_test = str(conftest.sofile)
    mod.lib = CDLL(_ctypes_test)


class TestStringPtr(BaseCTypesTestChecker):

    def test__POINTER_c_char(self):
        class X(Structure):
            _fields_ = [("str", POINTER(c_char))]
        x = X()

        # NULL pointer access
        raises(ValueError, getattr, x.str, "contents")
        b = c_buffer("Hello, World")
        #from sys import getrefcount as grc
        #assert grc(b) == 2
        x.str = b
        #assert grc(b) == 3

        # POINTER(c_char) and Python string is NOT compatible
        # POINTER(c_char) and c_buffer() is compatible
        for i in range(len(b)):
            assert b[i] == x.str[i]

        # XXX pypy  modified:
        #raises(TypeError, setattr, x, "str", "Hello, World")
        x = b = None
        py.test.skip("test passes! but modified to avoid getrefcount and detail issues")

    def test__c_char_p(self):
        class X(Structure):
            _fields_ = [("str", c_char_p)]
        x = X()

        # c_char_p and Python string is compatible
        # c_char_p and c_buffer is NOT compatible
        assert x.str == None
        x.str = "Hello, World"
        assert x.str == "Hello, World"
        # XXX pypy  modified:
        #b = c_buffer("Hello, World")
        #raises(TypeError, setattr, x, "str", b)
        x = None
        py.test.skip("test passes! but modified to avoid detail issues")


    def test_functions(self):
        strchr = lib.my_strchr
        strchr.restype = c_char_p

        # c_char_p and Python string is compatible
        # c_char_p and c_buffer are now compatible
        strchr.argtypes = c_char_p, c_char
        assert strchr("abcdef", "c") == "cdef"
        assert strchr(c_buffer("abcdef"), "c") == "cdef"

        # POINTER(c_char) and Python string is NOT compatible
        # POINTER(c_char) and c_buffer() is compatible
        strchr.argtypes = POINTER(c_char), c_char
        buf = c_buffer("abcdef")
        assert strchr(buf, "c") == "cdef"
        assert strchr("abcdef", "c") == "cdef"

        # XXX These calls are dangerous, because the first argument
        # to strchr is no longer valid after the function returns!
        # So we must keep a reference to buf separately

        strchr.restype = POINTER(c_char)
        buf = c_buffer("abcdef")
        r = strchr(buf, "c")
        x = r[0], r[1], r[2], r[3], r[4]
        assert x == ("c", "d", "e", "f", "\000")
        del buf
        # x1 will NOT be the same as x, usually:
        x1 = r[0], r[1], r[2], r[3], r[4]
