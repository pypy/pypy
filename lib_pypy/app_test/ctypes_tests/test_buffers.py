from ctypes import *
from support import BaseCTypesTestChecker

class TestStringBuffer(BaseCTypesTestChecker):

    def test_buffer(self):
        b = create_string_buffer(32)
        assert len(b) == 32
        assert sizeof(b) == 32 * sizeof(c_char)
        assert type(b[0]) is str

        b = create_string_buffer("abc")
        assert len(b) == 4 # trailing nul char
        assert sizeof(b) == 4 * sizeof(c_char)
        assert type(b[0]) is str
        assert b[0] == "a"
        assert b[:] == "abc\0"

    def test_string_conversion(self):
        b = create_string_buffer(u"abc")
        assert len(b) == 4 # trailing nul char
        assert sizeof(b) == 4 * sizeof(c_char)
        assert type(b[0]) is str
        assert b[0] == "a"
        assert b[:] == "abc\0"

    try:
        c_wchar
    except NameError:
        pass
    else:
        def test_unicode_buffer(self):
            b = create_unicode_buffer(32)
            assert len(b) == 32
            assert sizeof(b) == 32 * sizeof(c_wchar)
            assert type(b[0]) is unicode

            b = create_unicode_buffer(u"abc")
            assert len(b) == 4 # trailing nul char
            assert sizeof(b) == 4 * sizeof(c_wchar)
            assert type(b[0]) is unicode
            assert b[0] == u"a"
            assert b[:] == "abc\0"

        def test_unicode_conversion(self):
            b = create_unicode_buffer("abc")
            assert len(b) == 4 # trailing nul char
            assert sizeof(b) == 4 * sizeof(c_wchar)
            assert type(b[0]) is unicode
            assert b[0] == u"a"
            assert b[:] == "abc\0"

