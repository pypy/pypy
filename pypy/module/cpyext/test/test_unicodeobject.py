# encoding: iso-8859-15
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.unicodeobject import (
    Py_UNICODE, PyUnicodeObject, new_empty_unicode)
from pypy.module.cpyext.api import PyObjectP, PyObject
from pypy.module.cpyext.pyobject import Py_DecRef
from pypy.rpython.lltypesystem import rffi, lltype
import sys, py

class AppTestUnicodeObject(AppTestCpythonExtensionBase):
    def test_unicodeobject(self):
        module = self.import_extension('foo', [
            ("get_hello1", "METH_NOARGS",
             """
                 return PyUnicode_FromStringAndSize(
                     "Hello world<should not be included>", 11);
             """),
            ("test_GetSize", "METH_NOARGS",
             """
                 PyObject* s = PyUnicode_FromString("Hello world");
                 int result = 0;

                 if(PyUnicode_GetSize(s) == 11) {
                     result = 1;
                 }
                 if(s->ob_type->tp_basicsize != sizeof(void*)*4)
                     result = 0;
                 Py_DECREF(s);
                 return PyBool_FromLong(result);
             """),
            ("test_GetSize_exception", "METH_NOARGS",
             """
                 PyObject* f = PyFloat_FromDouble(1.0);
                 Py_ssize_t size = PyUnicode_GetSize(f);

                 Py_DECREF(f);
                 return NULL;
             """),
             ("test_is_unicode", "METH_VARARGS",
             """
                return PyBool_FromLong(PyUnicode_Check(PyTuple_GetItem(args, 0)));
             """)])
        assert module.get_hello1() == u'Hello world'
        assert module.test_GetSize()
        raises(TypeError, module.test_GetSize_exception)

        assert module.test_is_unicode(u"")
        assert not module.test_is_unicode(())

    def test_unicode_buffer_init(self):
        module = self.import_extension('foo', [
            ("getunicode", "METH_NOARGS",
             """
                 PyObject *s, *t;
                 Py_UNICODE* c;
                 Py_ssize_t len;

                 s = PyUnicode_FromUnicode(NULL, 4);
                 if (s == NULL)
                    return NULL;
                 t = PyUnicode_FromUnicode(NULL, 3);
                 if (t == NULL)
                    return NULL;
                 Py_DECREF(t);
                 c = PyUnicode_AsUnicode(s);
                 c[0] = 'a';
                 c[1] = 0xe9;
                 c[3] = 'c';
                 return s;
             """),
            ])
        s = module.getunicode()
        assert len(s) == 4
        assert s == u'aé\x00c'



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
        encoded_obj = api.PyUnicode_AsEncodedObject(space.wrap(u'späm'),
                                                utf_8, None)
        assert space.eq_w(encoded, encoded_obj)
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

    def test_unicode_resize(self, space, api):
        py_uni = new_empty_unicode(space, 10)
        ar = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        py_uni.c_buffer[0] = u'a'
        py_uni.c_buffer[1] = u'b'
        py_uni.c_buffer[2] = u'c'
        ar[0] = rffi.cast(PyObject, py_uni)
        api.PyUnicode_Resize(ar, 3)
        py_uni = rffi.cast(PyUnicodeObject, ar[0])
        assert py_uni.c_size == 3
        assert py_uni.c_buffer[1] == u'b'
        assert py_uni.c_buffer[3] == u'\x00'
        # the same for growing
        ar[0] = rffi.cast(PyObject, py_uni)
        api.PyUnicode_Resize(ar, 10)
        py_uni = rffi.cast(PyUnicodeObject, ar[0])
        assert py_uni.c_size == 10
        assert py_uni.c_buffer[1] == 'b'
        assert py_uni.c_buffer[10] == '\x00'
        Py_DecRef(space, ar[0])
        lltype.free(ar, flavor='raw')

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

    def test_TOTITLE(self, space, api):
        assert api.Py_UNICODE_TOTITLE(u'/') == u'/'
        assert api.Py_UNICODE_TOTITLE(u'ä') == u'Ä'
        assert api.Py_UNICODE_TOTITLE(u'Ä') == u'Ä'

    def test_TODECIMAL(self, space, api):
        assert api.Py_UNICODE_TODECIMAL(u'6') == 6
        assert api.Py_UNICODE_TODECIMAL(u'A') == -1

    def test_TODIGIT(self, space, api):
        assert api.Py_UNICODE_TODIGIT(u'6') == 6
        assert api.Py_UNICODE_TODIGIT(u'A') == -1

    def test_TONUMERIC(self, space, api):
        assert api.Py_UNICODE_TONUMERIC(u'6') == 6.0
        assert api.Py_UNICODE_TONUMERIC(u'A') == -1.0
        assert api.Py_UNICODE_TONUMERIC(u'\N{VULGAR FRACTION ONE HALF}') == .5

    def test_fromobject(self, space, api):
        w_u = space.wrap(u'a')
        assert api.PyUnicode_FromObject(w_u) is w_u
        assert space.unwrap(
            api.PyUnicode_FromObject(space.wrap('test'))) == 'test'

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
        self.raises(space, api, UnicodeEncodeError, api.PyUnicode_AsASCIIString, w_ustr)

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

    def test_compare(self, space, api):
        assert api.PyUnicode_Compare(space.wrap('a'), space.wrap('b')) == -1

    def test_copy(self, space, api):
        w_x = space.wrap(u"abcd\u0660")
        target_chunk, _ = rffi.alloc_unicodebuffer(space.int_w(space.len(w_x)))
        #lltype.malloc(Py_UNICODE, space.int_w(space.len(w_x)), flavor='raw')

        x_chunk = api.PyUnicode_AS_UNICODE(w_x)
        api.Py_UNICODE_COPY(target_chunk, x_chunk, 4)
        w_y = space.wrap(rffi.wcharpsize2unicode(target_chunk, 4))

        assert space.eq_w(w_y, space.wrap(u"abcd"))

        size = api.PyUnicode_GET_SIZE(w_x)
        api.Py_UNICODE_COPY(target_chunk, x_chunk, size)
        w_y = space.wrap(rffi.wcharpsize2unicode(target_chunk, size))

        assert space.eq_w(w_y, w_x)

        lltype.free(target_chunk, flavor='raw')

    def test_ascii_codec(self, space, api):
        s = 'abcdefg'
        data = rffi.str2charp(s)
        w_u = api.PyUnicode_DecodeASCII(data, len(s), lltype.nullptr(rffi.CCHARP.TO))
        assert space.eq_w(w_u, space.wrap(u"abcdefg"))
        rffi.free_charp(data)

        s = 'abcd\xFF'
        data = rffi.str2charp(s)
        self.raises(space, api, UnicodeDecodeError, api.PyUnicode_DecodeASCII,
                    data, len(s), lltype.nullptr(rffi.CCHARP.TO))
        rffi.free_charp(data)

        uni = u'abcdefg'
        data = rffi.unicode2wcharp(uni)
        w_s = api.PyUnicode_EncodeASCII(data, len(uni), lltype.nullptr(rffi.CCHARP.TO))
        assert space.eq_w(space.wrap("abcdefg"), w_s)
        rffi.free_wcharp(data)

        u = u'äbcdéfg'
        data = rffi.unicode2wcharp(u)
        w_s = api.PyUnicode_EncodeASCII(data, len(u), lltype.nullptr(rffi.CCHARP.TO))
        self.raises(space, api, UnicodeEncodeError, api.PyUnicode_EncodeASCII,
                    data, len(u), lltype.nullptr(rffi.CCHARP.TO))
        rffi.free_wcharp(data)

    def test_format(self, space, api):
        w_format = space.wrap(u'hi %s')
        w_args = space.wrap((u'test',))
        w_formated = api.PyUnicode_Format(w_format, w_args)
        assert space.unwrap(w_formated) == space.unwrap(space.mod(w_format, w_args))

    def test_join(self, space, api):
        w_sep = space.wrap(u'<sep>')
        w_seq = space.wrap([u'a', u'b'])
        w_joined = api.PyUnicode_Join(w_sep, w_seq)
        assert space.unwrap(w_joined) == u'a<sep>b'
