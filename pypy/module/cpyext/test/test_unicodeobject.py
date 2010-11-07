# encoding: iso-8859-15
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.unicodeobject import Py_UNICODE
from pypy.rpython.lltypesystem import rffi, lltype
import sys, py

class TestUnicode(BaseApiTest):
    def test_unicodeobject(self, space, api):
        assert api.PyUnicode_GET_SIZE(space.wrap(u'späm')) == 4
        assert api.PyUnicode_GetSize(space.wrap(u'späm')) == 4
        unichar = rffi.sizeof(Py_UNICODE)
        assert api.PyUnicode_GET_DATA_SIZE(space.wrap(u'späm')) == 4 * unichar

        encoding = rffi.charp2str(api.PyUnicode_GetDefaultEncoding())
        w_default_encoding = space.call_function(
            space.sys.get('getdefaultencoding')
        )
        assert encoding == space.unwrap(w_default_encoding)
        invalid = rffi.str2charp('invalid')
        utf_8 = rffi.str2charp('utf-8')
        prev_encoding = rffi.str2charp(space.unwrap(w_default_encoding))
        assert api.PyUnicode_SetDefaultEncoding(invalid) == -1
        assert api.PyErr_Occurred() is space.w_LookupError
        api.PyErr_Clear()
        assert api.PyUnicode_SetDefaultEncoding(utf_8) == 0
        assert rffi.charp2str(api.PyUnicode_GetDefaultEncoding()) == 'utf-8'
        assert api.PyUnicode_SetDefaultEncoding(prev_encoding) == 0
        rffi.free_charp(invalid)
        rffi.free_charp(utf_8)
        rffi.free_charp(prev_encoding)

    def test_AS(self, space, api):
        word = space.wrap(u'spam')
        array = rffi.cast(rffi.CWCHARP, api.PyUnicode_AS_DATA(word))
        array2 = api.PyUnicode_AS_UNICODE(word)
        array3 = api.PyUnicode_AsUnicode(word)
        for (i, char) in enumerate(space.unwrap(word)):
            assert array[i] == char
            assert array2[i] == char
            assert array3[i] == char
        self.raises(space, api, TypeError, api.PyUnicode_AsUnicode,
                    space.wrap('spam'))

        utf_8 = rffi.str2charp('utf-8')
        encoded = api.PyUnicode_AsEncodedString(space.wrap(u'späm'),
                                                utf_8, None)
        assert space.unwrap(encoded) == 'sp\xc3\xa4m'
        self.raises(space, api, TypeError, api.PyUnicode_AsEncodedString,
               space.newtuple([1, 2, 3]), None, None)
        self.raises(space, api, TypeError, api.PyUnicode_AsEncodedString,
               space.wrap(''), None, None)
        ascii = rffi.str2charp('ascii')
        replace = rffi.str2charp('replace')
        encoded = api.PyUnicode_AsEncodedString(space.wrap(u'späm'),
                                                ascii, replace)
        assert space.unwrap(encoded) == 'sp?m'
        rffi.free_charp(utf_8)
        rffi.free_charp(replace)
        rffi.free_charp(ascii)

        buf = rffi.unicode2wcharp(u"12345")
        api.PyUnicode_AsWideChar(space.wrap(u'longword'), buf, 5)
        assert rffi.wcharp2unicode(buf) == 'longw'
        api.PyUnicode_AsWideChar(space.wrap(u'a'), buf, 5)
        assert rffi.wcharp2unicode(buf) == 'a'
        rffi.free_wcharp(buf)

    def test_fromstring(self, space, api):
        s = rffi.str2charp(u'späm'.encode("utf-8"))
        w_res = api.PyUnicode_FromString(s)
        assert space.unwrap(w_res) == u'späm'

        w_res = api.PyUnicode_FromStringAndSize(s, 4)
        assert space.unwrap(w_res) == u'spä'
        rffi.free_charp(s)

    def test_AsUTF8String(self, space, api):
        w_u = space.wrap(u'späm')
        w_res = api.PyUnicode_AsUTF8String(w_u)
        assert space.type(w_res) is space.w_str
        assert space.unwrap(w_res) == 'sp\xc3\xa4m'
    
    def test_decode_utf8(self, space, api):
        u = rffi.str2charp(u'späm'.encode("utf-8"))
        w_u = api.PyUnicode_DecodeUTF8(u, 5, None)
        assert space.type(w_u) is space.w_unicode
        assert space.unwrap(w_u) == u'späm'
        
        w_u = api.PyUnicode_DecodeUTF8(u, 2, None)
        assert space.type(w_u) is space.w_unicode
        assert space.unwrap(w_u) == 'sp'
        rffi.free_charp(u)

    def test_IS(self, space, api):
        for char in [0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x1c, 0x1d, 0x1e, 0x1f,
                     0x20, 0x85, 0xa0, 0x1680, 0x2000, 0x2001, 0x2002,
                     0x2003, 0x2004, 0x2005, 0x2006, 0x2007, 0x2008,
                     0x2009, 0x200a,
                     #0x200b is in Other_Default_Ignorable_Code_Point in 4.1.0
                     0x2028, 0x2029, 0x202f, 0x205f, 0x3000]:
            assert api.Py_UNICODE_ISSPACE(unichr(char))
        assert not api.Py_UNICODE_ISSPACE(u'a')

        assert api.Py_UNICODE_ISDECIMAL(u'\u0660')
        assert not api.Py_UNICODE_ISDECIMAL(u'a')

        for char in [0x0a, 0x0d, 0x1c, 0x1d, 0x1e, 0x85, 0x2028, 0x2029]:
            assert api.Py_UNICODE_ISLINEBREAK(unichr(char))

        assert api.Py_UNICODE_ISLOWER(u'ä')
        assert not api.Py_UNICODE_ISUPPER(u'ä')
        assert api.Py_UNICODE_ISLOWER(u'a')
        assert not api.Py_UNICODE_ISUPPER(u'a')
        assert not api.Py_UNICODE_ISLOWER(u'Ä')
        assert api.Py_UNICODE_ISUPPER(u'Ä')

    def test_TOLOWER(self, space, api):
        assert api.Py_UNICODE_TOLOWER(u'ä') == u'ä'
        assert api.Py_UNICODE_TOLOWER(u'Ä') == u'ä'

    def test_TOUPPER(self, space, api):
        assert api.Py_UNICODE_TOUPPER(u'ä') == u'Ä'
        assert api.Py_UNICODE_TOUPPER(u'Ä') == u'Ä'

    def test_decode(self, space, api):
        b_text = rffi.str2charp('caf\x82xx')
        b_encoding = rffi.str2charp('cp437')
        assert space.unwrap(
            api.PyUnicode_Decode(b_text, 4, b_encoding, None)) == u'caf\xe9'

        w_text = api.PyUnicode_FromEncodedObject(space.wrap("test"), b_encoding, None)
        assert space.is_true(space.isinstance(w_text, space.w_unicode))
        assert space.unwrap(w_text) == "test"

        assert api.PyUnicode_FromEncodedObject(space.wrap(u"test"), b_encoding, None) is None
        assert api.PyErr_Occurred() is space.w_TypeError
        assert api.PyUnicode_FromEncodedObject(space.wrap(1), b_encoding, None) is None
        assert api.PyErr_Occurred() is space.w_TypeError
        api.PyErr_Clear()

        rffi.free_charp(b_text)
        rffi.free_charp(b_encoding)

    def test_leak(self):
        size = 50
        raw_buf, gc_buf = rffi.alloc_buffer(size)
        for i in range(size): raw_buf[i] = 'a'
        str = rffi.str_from_buffer(raw_buf, gc_buf, size, size)
        rffi.keep_buffer_alive_until_here(raw_buf, gc_buf)

    def test_mbcs(self, space, api):
        if sys.platform != 'win32':
            py.test.skip("mcbs encoding only exists on Windows")
        # unfortunately, mbcs is locale-dependent.
        # This tests works at least on a Western Windows.
        unichars = u"abc" + unichr(12345)
        wbuf = rffi.unicode2wcharp(unichars)
        w_str = api.PyUnicode_EncodeMBCS(wbuf, 4, None)
        rffi.free_wcharp(wbuf)
        assert space.type(w_str) is space.w_str
        assert space.str_w(w_str) == "abc?"

    def test_escape(self, space, api):
        def test(ustr):
            w_ustr = space.wrap(ustr.decode('Unicode-Escape'))
            result = api.PyUnicode_AsUnicodeEscapeString(w_ustr)
            assert space.eq_w(space.wrap(ustr), result)

        test('\\u674f\\u7f8e')
        test('\\u0105\\u0107\\u017c\\u017a')
        test('El Ni\\xf1o')

    def test_ascii(self, space, api):
        ustr = "abcdef"
        w_ustr = space.wrap(ustr.decode("ascii"))
        result = api.PyUnicode_AsASCIIString(w_ustr)
        
        assert space.eq_w(space.wrap(ustr), result)

        w_ustr = space.wrap(u"abcd\xe9f")
        result = api.PyUnicode_AsASCIIString(w_ustr)
        assert result is None

    def test_decode_utf16(self, space, api):
        def test(encoded, endian, realendian=None):
            encoded_charp = rffi.str2charp(encoded)
            strict_charp = rffi.str2charp("strict")
            if endian is not None:
                if endian < 0:
                    value = -1
                elif endian > 0:
                    value = 1
                else:
                    value = 0
                pendian = lltype.malloc(rffi.INTP.TO, 1, flavor='raw')
                pendian[0] = rffi.cast(rffi.INT, value)
            else:
                pendian = None

            w_ustr = api.PyUnicode_DecodeUTF16(encoded_charp, len(encoded), strict_charp, pendian)
            assert space.eq_w(space.call_method(w_ustr, 'encode', space.wrap('ascii')),
                              space.wrap("abcd"))

            rffi.free_charp(encoded_charp)
            rffi.free_charp(strict_charp)
            if pendian:
                if realendian is not None:
                    assert rffi.cast(rffi.INT, realendian) == pendian[0]
                lltype.free(pendian, flavor='raw')

        test("\x61\x00\x62\x00\x63\x00\x64\x00", -1)

        test("\x61\x00\x62\x00\x63\x00\x64\x00", None)

        test("\x00\x61\x00\x62\x00\x63\x00\x64", 1)

        test("\xFE\xFF\x00\x61\x00\x62\x00\x63\x00\x64", 0, 1)
        test("\xFF\xFE\x61\x00\x62\x00\x63\x00\x64\x00", 0, -1)
