# encoding: utf-8
import pytest
from pypy.module.cpyext.test.test_api import BaseApiTest, raises_w
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.unicodeobject import (
    Py_UNICODE, PyUnicodeObject, new_empty_unicode)
from pypy.module.cpyext.api import PyObjectP, PyObject
from pypy.module.cpyext.pyobject import Py_DecRef, from_ref
from rpython.rtyper.lltypesystem import rffi, lltype
import sys, py
from pypy.module.cpyext.unicodeobject import *

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

                 if(PyUnicode_GetSize(s) != 11) {
                     result = -PyUnicode_GetSize(s);
                 }
#ifdef PYPY_VERSION
                 // Slightly silly test that tp_basicsize is reasonable.
                 if(s->ob_type->tp_basicsize != sizeof(void*)*7)
                     result = s->ob_type->tp_basicsize;
#endif  // PYPY_VERSION
                 Py_DECREF(s);
                 return PyLong_FromLong(result);
             """),
            ("test_GetSize_exception", "METH_NOARGS",
             """
                 PyObject* f = PyFloat_FromDouble(1.0);
                 PyUnicode_GetSize(f);

                 Py_DECREF(f);
                 return NULL;
             """),
             ("test_is_unicode", "METH_VARARGS",
             """
                return PyBool_FromLong(PyUnicode_Check(PyTuple_GetItem(args, 0)));
             """)])
        assert module.get_hello1() == u'Hello world'
        assert module.test_GetSize() == 0
        raises(TypeError, module.test_GetSize_exception)

        assert module.test_is_unicode(u"")
        assert not module.test_is_unicode(())

    def test_unicode_buffer_init(self):
        module = self.import_extension('foo', [
            ("getunicode", "METH_NOARGS",
             """
                 PyObject *s, *t;
                 Py_UNICODE* c;

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
                 c[2] = 0x00;
                 c[3] = 'c';
                 return s;
             """),
            ])
        s = module.getunicode()
        assert len(s) == 4
        assert s == u'a\xe9\x00c'

    def test_hash(self):
        module = self.import_extension('foo', [
            ("test_hash", "METH_VARARGS",
             '''
                PyObject* obj = (PyTuple_GetItem(args, 0));
                long hash = ((PyUnicodeObject*)obj)->hash;
                return PyLong_FromLong(hash);
             '''
             ),
            ])
        obj = u'xyz'
        # CPython in particular does not precompute ->hash, so we need to call
        # hash() first.
        expected_hash = hash(obj)
        assert module.test_hash(obj) == expected_hash

    def test_default_encoded_string(self):
        module = self.import_extension('foo', [
            ("test_default_encoded_string", "METH_O",
             '''
                PyObject* result = _PyUnicode_AsDefaultEncodedString(args, "replace");
                Py_INCREF(result);
                return result;
             '''
             ),
            ])
        res = module.test_default_encoded_string(u"xyz")
        assert isinstance(res, str)
        assert res == 'xyz'
        res = module.test_default_encoded_string(u"caf\xe9")
        assert isinstance(res, str)
        assert res == 'caf?'

    def test_unicode_macros(self):
        """The PyUnicode_* macros cast, and calls expecting that build."""
        module = self.import_extension('foo', [
             ("test_macro_invocations", "METH_NOARGS",
             """
                PyObject* o = PyUnicode_FromString("");
                PyUnicodeObject* u = (PyUnicodeObject*)o;

                PyUnicode_GET_SIZE(u);
                PyUnicode_GET_SIZE(o);

                PyUnicode_GET_DATA_SIZE(u);
                PyUnicode_GET_DATA_SIZE(o);

                PyUnicode_AS_UNICODE(o);
                PyUnicode_AS_UNICODE(u);
                return o;
             """)])
        assert module.test_macro_invocations() == u''

    def test_format(self):
        module = self.import_extension('foo', [
            ("test_unicode_format", "METH_VARARGS",
             '''
                 return PyUnicode_FromFormat("bla %d ble %s\\n",
                        PyInt_AsLong(PyTuple_GetItem(args, 0)),
                        PyString_AsString(PyTuple_GetItem(args, 1)));
             '''
             )
            ])
        res = module.test_unicode_format(1, "xyz")
        assert res == u"bla 1 ble xyz\n"


class TestUnicode(BaseApiTest):
    def test_unicodeobject(self, space):
        assert PyUnicode_GET_SIZE(space, space.wrap(u'sp�m')) == 4
        assert PyUnicode_GetSize(space, space.wrap(u'sp�m')) == 4
        unichar = rffi.sizeof(Py_UNICODE)
        assert PyUnicode_GET_DATA_SIZE(space, space.wrap(u'sp�m')) == 4 * unichar

        encoding = rffi.charp2str(PyUnicode_GetDefaultEncoding(space, ))
        w_default_encoding = space.call_function(
            space.sys.get('getdefaultencoding')
        )
        assert encoding == space.unwrap(w_default_encoding)
        invalid = rffi.str2charp('invalid')
        utf_8 = rffi.str2charp('utf-8')
        prev_encoding = rffi.str2charp(space.unwrap(w_default_encoding))
        with raises_w(space, TypeError):
            PyUnicode_SetDefaultEncoding(space, lltype.nullptr(rffi.CCHARP.TO))
        with raises_w(space, LookupError):
            PyUnicode_SetDefaultEncoding(space, invalid)

        assert PyUnicode_SetDefaultEncoding(space, utf_8) == 0
        assert rffi.charp2str(PyUnicode_GetDefaultEncoding(space, )) == 'utf-8'
        assert PyUnicode_SetDefaultEncoding(space, prev_encoding) == 0
        rffi.free_charp(invalid)
        rffi.free_charp(utf_8)
        rffi.free_charp(prev_encoding)

    def test_AS(self, space):
        word = space.wrap(u'spam')
        array = rffi.cast(rffi.CWCHARP, PyUnicode_AS_DATA(space, word))
        array2 = PyUnicode_AS_UNICODE(space, word)
        array3 = PyUnicode_AsUnicode(space, word)
        for (i, char) in enumerate(space.unwrap(word)):
            assert array[i] == char
            assert array2[i] == char
            assert array3[i] == char
        with raises_w(space, TypeError):
            PyUnicode_AsUnicode(space, space.wrap('spam'))

        utf_8 = rffi.str2charp('utf-8')
        encoded = PyUnicode_AsEncodedString(space, space.wrap(u'sp�m'),
                                                utf_8, None)
        assert space.unwrap(encoded) == 'sp\xef\xbf\xbdm'
        encoded_obj = PyUnicode_AsEncodedObject(space, space.wrap(u'sp�m'),
                                                utf_8, None)
        assert space.eq_w(encoded, encoded_obj)
        with raises_w(space, TypeError):
            PyUnicode_AsEncodedString(
                space, space.newtuple([1, 2, 3]), None, None)
        with raises_w(space, TypeError):
            PyUnicode_AsEncodedString(space, space.wrap(''), None, None)
        ascii = rffi.str2charp('ascii')
        replace = rffi.str2charp('replace')
        encoded = PyUnicode_AsEncodedString(space, space.wrap(u'sp�m'),
                                                ascii, replace)
        assert space.unwrap(encoded) == 'sp?m'
        rffi.free_charp(utf_8)
        rffi.free_charp(replace)
        rffi.free_charp(ascii)

        buf = rffi.unicode2wcharp(u"12345")
        PyUnicode_AsWideChar(space, space.wrap(u'longword'), buf, 5)
        assert rffi.wcharp2unicode(buf) == 'longw'
        PyUnicode_AsWideChar(space, space.wrap(u'a'), buf, 5)
        assert rffi.wcharp2unicode(buf) == 'a'
        rffi.free_wcharp(buf)

    def test_fromstring(self, space):
        s = rffi.str2charp(u'sp\x09m'.encode("utf-8"))
        w_res = PyUnicode_FromString(space, s)
        assert space.unwrap(w_res) == u'sp\x09m'

        res = PyUnicode_FromStringAndSize(space, s, 4)
        w_res = from_ref(space, res)
        Py_DecRef(space, res)
        assert space.unwrap(w_res) == u'sp\x09m'
        rffi.free_charp(s)

    def test_unicode_resize(self, space):
        py_uni = new_empty_unicode(space, 10)
        ar = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        py_uni.c_str[0] = u'a'
        py_uni.c_str[1] = u'b'
        py_uni.c_str[2] = u'c'
        ar[0] = rffi.cast(PyObject, py_uni)
        PyUnicode_Resize(space, ar, 3)
        py_uni = rffi.cast(PyUnicodeObject, ar[0])
        assert py_uni.c_length == 3
        assert py_uni.c_str[1] == u'b'
        assert py_uni.c_str[3] == u'\x00'
        # the same for growing
        ar[0] = rffi.cast(PyObject, py_uni)
        PyUnicode_Resize(space, ar, 10)
        py_uni = rffi.cast(PyUnicodeObject, ar[0])
        assert py_uni.c_length == 10
        assert py_uni.c_str[1] == 'b'
        assert py_uni.c_str[10] == '\x00'
        Py_DecRef(space, ar[0])
        lltype.free(ar, flavor='raw')

    def test_AsUTF8String(self, space):
        w_u = space.wrap(u'sp\x09m')
        w_res = PyUnicode_AsUTF8String(space, w_u)
        assert space.type(w_res) is space.w_bytes
        assert space.unwrap(w_res) == 'sp\tm'

    def test_decode_utf8(self, space):
        u = rffi.str2charp(u'sp\x134m'.encode("utf-8"))
        w_u = PyUnicode_DecodeUTF8(space, u, 5, None)
        assert space.type(w_u) is space.w_unicode
        assert space.unwrap(w_u) == u'sp\x134m'

        w_u = PyUnicode_DecodeUTF8(space, u, 2, None)
        assert space.type(w_u) is space.w_unicode
        assert space.unwrap(w_u) == 'sp'
        rffi.free_charp(u)

    def test_encode_utf8(self, space):
        u = rffi.unicode2wcharp(u'sp\x09m')
        w_s = PyUnicode_EncodeUTF8(space, u, 4, None)
        assert space.unwrap(w_s) == u'sp\x09m'.encode('utf-8')
        rffi.free_wcharp(u)

    def test_encode_decimal(self, space):
        with rffi.scoped_unicode2wcharp(u' (12, 35 ABC)') as u:
            with rffi.scoped_alloc_buffer(20) as buf:
                res = PyUnicode_EncodeDecimal(space, u, 13, buf.raw, None)
                s = rffi.charp2str(buf.raw)
        assert res == 0
        assert s == ' (12, 35 ABC)'

        with rffi.scoped_unicode2wcharp(u' (12, \u1234\u1235)') as u:
            with rffi.scoped_alloc_buffer(20) as buf:
                with pytest.raises(OperationError):
                    PyUnicode_EncodeDecimal(space, u, 9, buf.raw, None)

        with rffi.scoped_unicode2wcharp(u' (12, \u1234\u1235)') as u:
            with rffi.scoped_alloc_buffer(20) as buf:
                with rffi.scoped_str2charp("replace") as errors:
                    res = PyUnicode_EncodeDecimal(space, u, 9, buf.raw,
                                                      errors)
                s = rffi.charp2str(buf.raw)
        assert res == 0
        assert s == " (12, ??)"

        with rffi.scoped_unicode2wcharp(u'12\u1234') as u:
            with rffi.scoped_alloc_buffer(20) as buf:
                with rffi.scoped_str2charp("xmlcharrefreplace") as errors:
                    res = PyUnicode_EncodeDecimal(space, u, 3, buf.raw,
                                                      errors)
                s = rffi.charp2str(buf.raw)
        assert res == 0
        assert s == "12&#4660;"


    def test_IS(self, space):
        for char in [0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x1c, 0x1d, 0x1e, 0x1f,
                     0x20, 0x85, 0xa0, 0x1680, 0x2000, 0x2001, 0x2002,
                     0x2003, 0x2004, 0x2005, 0x2006, 0x2007, 0x2008,
                     0x2009, 0x200a,
                     #0x200b is in Other_Default_Ignorable_Code_Point in 4.1.0
                     0x2028, 0x2029, 0x202f, 0x205f, 0x3000]:
            assert Py_UNICODE_ISSPACE(space, unichr(char))
        assert not Py_UNICODE_ISSPACE(space, u'a')

        assert Py_UNICODE_ISALPHA(space, u'a')
        assert not Py_UNICODE_ISALPHA(space, u'0')
        assert Py_UNICODE_ISALNUM(space, u'a')
        assert Py_UNICODE_ISALNUM(space, u'0')
        assert not Py_UNICODE_ISALNUM(space, u'+')

        assert Py_UNICODE_ISDECIMAL(space, u'\u0660')
        assert not Py_UNICODE_ISDECIMAL(space, u'a')
        assert Py_UNICODE_ISDIGIT(space, u'9')
        assert not Py_UNICODE_ISDIGIT(space, u'@')
        assert Py_UNICODE_ISNUMERIC(space, u'9')
        assert not Py_UNICODE_ISNUMERIC(space, u'@')

        for char in [0x0a, 0x0d, 0x1c, 0x1d, 0x1e, 0x85, 0x2028, 0x2029]:
            assert Py_UNICODE_ISLINEBREAK(space, unichr(char))

        assert Py_UNICODE_ISLOWER(space, u'\xdf') # sharp s
        assert Py_UNICODE_ISUPPER(space, u'\xde') # capital thorn
        assert Py_UNICODE_ISLOWER(space, u'a')
        assert not Py_UNICODE_ISUPPER(space, u'a')
        assert not Py_UNICODE_ISTITLE(space, u'\xce')
        assert Py_UNICODE_ISTITLE(space,
            u'\N{LATIN CAPITAL LETTER L WITH SMALL LETTER J}')

    def test_TOLOWER(self, space):
        assert Py_UNICODE_TOLOWER(space, u'�') == u'�'
        assert Py_UNICODE_TOLOWER(space, u'�') == u'�'

    def test_TOUPPER(self, space):
        assert Py_UNICODE_TOUPPER(space, u'�') == u'�'
        assert Py_UNICODE_TOUPPER(space, u'�') == u'�'

    def test_TOTITLE(self, space):
        assert Py_UNICODE_TOTITLE(space, u'/') == u'/'
        assert Py_UNICODE_TOTITLE(space, u'�') == u'�'
        assert Py_UNICODE_TOTITLE(space, u'�') == u'�'

    def test_TODECIMAL(self, space):
        assert Py_UNICODE_TODECIMAL(space, u'6') == 6
        assert Py_UNICODE_TODECIMAL(space, u'A') == -1

    def test_TODIGIT(self, space):
        assert Py_UNICODE_TODIGIT(space, u'6') == 6
        assert Py_UNICODE_TODIGIT(space, u'A') == -1

    def test_TONUMERIC(self, space):
        assert Py_UNICODE_TONUMERIC(space, u'6') == 6.0
        assert Py_UNICODE_TONUMERIC(space, u'A') == -1.0
        assert Py_UNICODE_TONUMERIC(space, u'\N{VULGAR FRACTION ONE HALF}') == .5

    def test_fromobject(self, space):
        w_u = space.wrap(u'a')
        assert PyUnicode_FromObject(space, w_u) is w_u
        assert space.unwrap(
            PyUnicode_FromObject(space, space.wrap('test'))) == 'test'

    def test_decode(self, space):
        b_text = rffi.str2charp('caf\x82xx')
        b_encoding = rffi.str2charp('cp437')
        assert space.unwrap(
            PyUnicode_Decode(space, b_text, 4, b_encoding, None)) == u'caf\xe9'

        w_text = PyUnicode_FromEncodedObject(space, space.wrap("test"), b_encoding, None)
        assert space.isinstance_w(w_text, space.w_unicode)
        assert space.unwrap(w_text) == "test"

        with raises_w(space, TypeError):
            PyUnicode_FromEncodedObject(space, space.wrap(u"test"),
                                        b_encoding, None)
        with raises_w(space, TypeError):
            PyUnicode_FromEncodedObject(space, space.wrap(1), b_encoding, None)

        rffi.free_charp(b_text)
        rffi.free_charp(b_encoding)

    def test_decode_null_encoding(self, space):
        null_charp = lltype.nullptr(rffi.CCHARP.TO)
        u_text = u'abcdefg'
        s_text = space.str_w(PyUnicode_AsEncodedString(space, space.wrap(u_text), null_charp, null_charp))
        b_text = rffi.str2charp(s_text)
        assert space.unwrap(PyUnicode_Decode(space, b_text, len(s_text), null_charp, null_charp)) == u_text
        with raises_w(space, TypeError):
            PyUnicode_FromEncodedObject(
                space, space.wrap(u_text), null_charp, None)
        rffi.free_charp(b_text)

    def test_mbcs(self, space):
        if sys.platform != 'win32':
            py.test.skip("mcbs encoding only exists on Windows")
        # unfortunately, mbcs is locale-dependent.
        # This tests works at least on a Western Windows.
        unichars = u"abc" + unichr(12345)
        wbuf = rffi.unicode2wcharp(unichars)
        w_bytes = PyUnicode_EncodeMBCS(space, wbuf, 4, None)
        rffi.free_wcharp(wbuf)
        assert space.type(w_bytes) is space.w_bytes
        assert space.str_w(w_bytes) == "abc?"

    def test_escape(self, space):
        def test(ustr):
            w_ustr = space.wrap(ustr.decode('Unicode-Escape'))
            result = PyUnicode_AsUnicodeEscapeString(space, w_ustr)
            assert space.eq_w(space.wrap(ustr), result)

        test('\\u674f\\u7f8e')
        test('\\u0105\\u0107\\u017c\\u017a')
        test('El Ni\\xf1o')

    def test_ascii(self, space):
        ustr = "abcdef"
        w_ustr = space.wrap(ustr.decode("ascii"))
        result = PyUnicode_AsASCIIString(space, w_ustr)
        assert space.eq_w(space.wrap(ustr), result)
        with raises_w(space, UnicodeEncodeError):
            PyUnicode_AsASCIIString(space, space.wrap(u"abcd\xe9f"))

    def test_decode_utf16(self, space):
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

            w_ustr = PyUnicode_DecodeUTF16(space, encoded_charp, len(encoded), strict_charp, pendian)
            assert space.eq_w(space.call_method(w_ustr, 'encode', space.wrap('ascii')),
                              space.wrap("abcd"))

            rffi.free_charp(encoded_charp)
            rffi.free_charp(strict_charp)
            if pendian:
                if realendian is not None:
                    assert rffi.cast(rffi.INT, realendian) == pendian[0]
                lltype.free(pendian, flavor='raw')

        test("\x61\x00\x62\x00\x63\x00\x64\x00", -1)
        if sys.byteorder == 'big':
            test("\x00\x61\x00\x62\x00\x63\x00\x64", None)
        else:
            test("\x61\x00\x62\x00\x63\x00\x64\x00", None)
        test("\x00\x61\x00\x62\x00\x63\x00\x64", 1)
        test("\xFE\xFF\x00\x61\x00\x62\x00\x63\x00\x64", 0, 1)
        test("\xFF\xFE\x61\x00\x62\x00\x63\x00\x64\x00", 0, -1)

    def test_decode_utf32(self, space):
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

            w_ustr = PyUnicode_DecodeUTF32(space, encoded_charp, len(encoded),
                                           strict_charp, pendian)
            assert space.eq_w(space.call_method(w_ustr, 'encode', space.wrap('ascii')),
                              space.wrap("ab"))

            rffi.free_charp(encoded_charp)
            rffi.free_charp(strict_charp)
            if pendian:
                if realendian is not None:
                    assert rffi.cast(rffi.INT, realendian) == pendian[0]
                lltype.free(pendian, flavor='raw')

        test("\x61\x00\x00\x00\x62\x00\x00\x00", -1)

        if sys.byteorder == 'big':
            test("\x00\x00\x00\x61\x00\x00\x00\x62", None)
        else:
            test("\x61\x00\x00\x00\x62\x00\x00\x00", None)

        test("\x00\x00\x00\x61\x00\x00\x00\x62", 1)

        test("\x00\x00\xFE\xFF\x00\x00\x00\x61\x00\x00\x00\x62", 0, 1)
        test("\xFF\xFE\x00\x00\x61\x00\x00\x00\x62\x00\x00\x00", 0, -1)

    def test_compare(self, space):
        assert PyUnicode_Compare(space, space.wrap('a'), space.wrap('b')) == -1

    def test_concat(self, space):
        w_res = PyUnicode_Concat(space, space.wrap(u'a'), space.wrap(u'b'))
        assert space.unwrap(w_res) == u'ab'

    def test_copy(self, space):
        w_x = space.wrap(u"abcd\u0660")
        count1 = space.int_w(space.len(w_x))
        target_chunk = lltype.malloc(rffi.CWCHARP.TO, count1, flavor='raw')

        x_chunk = PyUnicode_AS_UNICODE(space, w_x)
        Py_UNICODE_COPY(space, target_chunk, x_chunk, 4)
        w_y = space.wrap(rffi.wcharpsize2unicode(target_chunk, 4))

        assert space.eq_w(w_y, space.wrap(u"abcd"))

        size = PyUnicode_GET_SIZE(space, w_x)
        Py_UNICODE_COPY(space, target_chunk, x_chunk, size)
        w_y = space.wrap(rffi.wcharpsize2unicode(target_chunk, size))

        assert space.eq_w(w_y, w_x)

        lltype.free(target_chunk, flavor='raw')

    def test_ascii_codec(self, space):
        s = 'abcdefg'
        data = rffi.str2charp(s)
        NULL = lltype.nullptr(rffi.CCHARP.TO)
        w_u = PyUnicode_DecodeASCII(space, data, len(s), NULL)
        assert space.eq_w(w_u, space.wrap(u"abcdefg"))
        rffi.free_charp(data)

        s = 'abcd\xFF'
        data = rffi.str2charp(s)
        with raises_w(space, UnicodeDecodeError):
            PyUnicode_DecodeASCII(space, data, len(s), NULL)
        rffi.free_charp(data)

        uni = u'abcdefg'
        data = rffi.unicode2wcharp(uni)
        w_s = PyUnicode_EncodeASCII(space, data, len(uni), NULL)
        assert space.eq_w(space.wrap("abcdefg"), w_s)
        rffi.free_wcharp(data)

        u = u'�bcd�fg'
        data = rffi.unicode2wcharp(u)
        with raises_w(space, UnicodeEncodeError):
            PyUnicode_EncodeASCII(space, data, len(u), NULL)
        rffi.free_wcharp(data)

    def test_latin1(self, space):
        s = 'abcdefg'
        data = rffi.str2charp(s)
        w_u = PyUnicode_DecodeLatin1(space, data, len(s),
                                     lltype.nullptr(rffi.CCHARP.TO))
        assert space.eq_w(w_u, space.wrap(u"abcdefg"))
        rffi.free_charp(data)

        uni = u'abcdefg'
        data = rffi.unicode2wcharp(uni)
        w_s = PyUnicode_EncodeLatin1(space, data, len(uni),
                                     lltype.nullptr(rffi.CCHARP.TO))
        assert space.eq_w(space.wrap("abcdefg"), w_s)
        rffi.free_wcharp(data)

        ustr = "abcdef"
        w_ustr = space.wrap(ustr.decode("ascii"))
        result = PyUnicode_AsLatin1String(space, w_ustr)
        assert space.eq_w(space.wrap(ustr), result)

    def test_format(self, space):
        w_format = space.wrap(u'hi %s')
        w_args = space.wrap((u'test',))
        w_formated = PyUnicode_Format(space, w_format, w_args)
        assert space.unwrap(w_formated) == space.unwrap(space.mod(w_format, w_args))

    def test_join(self, space):
        w_sep = space.wrap(u'<sep>')
        w_seq = space.wrap([u'a', u'b'])
        w_joined = PyUnicode_Join(space, w_sep, w_seq)
        assert space.unwrap(w_joined) == u'a<sep>b'

    def test_fromordinal(self, space):
        w_char = PyUnicode_FromOrdinal(space, 65)
        assert space.unwrap(w_char) == u'A'
        w_char = PyUnicode_FromOrdinal(space, 0)
        assert space.unwrap(w_char) == u'\0'
        w_char = PyUnicode_FromOrdinal(space, 0xFFFF)
        assert space.unwrap(w_char) == u'\uFFFF'

    def test_replace(self, space):
        w_str = space.wrap(u"abababab")
        w_substr = space.wrap(u"a")
        w_replstr = space.wrap(u"z")
        assert u"zbzbabab" == space.unwrap(
            PyUnicode_Replace(space, w_str, w_substr, w_replstr, 2))
        assert u"zbzbzbzb" == space.unwrap(
            PyUnicode_Replace(space, w_str, w_substr, w_replstr, -1))

    def test_tailmatch(self, space):
        w_str = space.wrap(u"abcdef")
        # prefix match
        assert PyUnicode_Tailmatch(space, w_str, space.wrap("cde"), 2, 9, -1) == 1
        assert PyUnicode_Tailmatch(space, w_str, space.wrap("cde"), 2, 4, -1) == 0 # ends at 'd'
        assert PyUnicode_Tailmatch(space, w_str, space.wrap("cde"), 1, 6, -1) == 0 # starts at 'b'
        assert PyUnicode_Tailmatch(space, w_str, space.wrap("cdf"), 2, 6, -1) == 0
        # suffix match
        assert PyUnicode_Tailmatch(space, w_str, space.wrap("cde"), 1, 5,  1) == 1
        assert PyUnicode_Tailmatch(space, w_str, space.wrap("cde"), 3, 5,  1) == 0 # starts at 'd'
        assert PyUnicode_Tailmatch(space, w_str, space.wrap("cde"), 1, 6,  1) == 0 # ends at 'f'
        assert PyUnicode_Tailmatch(space, w_str, space.wrap("bde"), 1, 5,  1) == 0
        # type checks
        with raises_w(space, TypeError):
            PyUnicode_Tailmatch(space, w_str, space.wrap(3), 2, 10, 1)
        with raises_w(space, TypeError):
            PyUnicode_Tailmatch(
                space, space.wrap(3), space.wrap("abc"), 2, 10, 1)

    def test_count(self, space):
        w_str = space.wrap(u"abcabdab")
        assert PyUnicode_Count(space, w_str, space.wrap(u"ab"), 0, -1) == 2
        assert PyUnicode_Count(space, w_str, space.wrap(u"ab"), 0, 2) == 1
        assert PyUnicode_Count(space, w_str, space.wrap(u"ab"), -5, 30) == 2

    def test_find(self, space):
        w_str = space.wrap(u"abcabcd")
        assert PyUnicode_Find(space, w_str, space.wrap(u"c"), 0, 7, 1) == 2
        assert PyUnicode_Find(space, w_str, space.wrap(u"c"), 3, 7, 1) == 5
        assert PyUnicode_Find(space, w_str, space.wrap(u"c"), 0, 7, -1) == 5
        assert PyUnicode_Find(space, w_str, space.wrap(u"c"), 3, 7, -1) == 5
        assert PyUnicode_Find(space, w_str, space.wrap(u"c"), 0, 4, -1) == 2
        assert PyUnicode_Find(space, w_str, space.wrap(u"z"), 0, 4, -1) == -1

    def test_split(self, space):
        w_str = space.wrap(u"a\nb\nc\nd")
        assert "[u'a', u'b', u'c', u'd']" == space.unwrap(space.repr(
                PyUnicode_Split(space, w_str, space.wrap('\n'), -1)))
        assert r"[u'a', u'b', u'c\nd']" == space.unwrap(space.repr(
                PyUnicode_Split(space, w_str, space.wrap('\n'), 2)))
        assert r"[u'a', u'b', u'c d']" == space.unwrap(space.repr(
                PyUnicode_Split(space, space.wrap(u'a\nb  c d'), None, 2)))
        assert "[u'a', u'b', u'c', u'd']" == space.unwrap(space.repr(
                PyUnicode_Splitlines(space, w_str, 0)))
        assert r"[u'a\n', u'b\n', u'c\n', u'd']" == space.unwrap(space.repr(
                PyUnicode_Splitlines(space, w_str, 1)))
