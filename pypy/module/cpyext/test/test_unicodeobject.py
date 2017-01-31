# encoding: utf-8
import pytest
from pypy.module.cpyext.test.test_api import BaseApiTest, raises_w
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.unicodeobject import (
    Py_UNICODE, PyUnicodeObject, new_empty_unicode)
from pypy.module.cpyext.api import PyObjectP, PyObject, Py_CLEANUP_SUPPORTED
from pypy.module.cpyext.pyobject import Py_DecRef, from_ref
from rpython.rtyper.lltypesystem import rffi, lltype
import sys, py
from pypy.module.cpyext.unicodeobject import *
from pypy.module.cpyext.unicodeobject import _PyUnicode_Ready

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
                 if(s->ob_type->tp_basicsize != sizeof(void*)*12)
                     result = s->ob_type->tp_basicsize;
#endif  // PYPY_VERSION
                 Py_DECREF(s);
                 return PyLong_FromLong(result);
             """),
            ("test_GetLength", "METH_NOARGS",
             """
                 PyObject* s = PyUnicode_FromString("Hello world");
                 int result = 0;

                 if(PyUnicode_GetLength(s) != 11) {
                     result = -PyUnicode_GetSize(s);
                 }
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

        # XXX: needs a test where it differs from GetSize
        assert module.test_GetLength() == 0

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

    def test_format_v(self):
        module = self.import_extension('foo', [
            ("test_unicode_format_v", "METH_VARARGS",
             '''
                 return helper("bla %d ble %s\\n",
                        PyLong_AsLong(PyTuple_GetItem(args, 0)),
                        _PyUnicode_AsString(PyTuple_GetItem(args, 1)));
             '''
             )
            ], prologue='''
            PyObject* helper(char* fmt, ...)
            {
              va_list va;
              PyObject* res;
              va_start(va, fmt);
              res = PyUnicode_FromFormatV(fmt, va);
              va_end(va);
              return res;
            }
            ''')
        res = module.test_unicode_format_v(1, "xyz")
        assert res == "bla 1 ble xyz\n"

    def test_format(self):
        module = self.import_extension('foo', [
            ("test_unicode_format", "METH_VARARGS",
             '''
                 return PyUnicode_FromFormat("bla %d ble %s\\n",
                        PyLong_AsLong(PyTuple_GetItem(args, 0)),
                        _PyUnicode_AsString(PyTuple_GetItem(args, 1)));
             '''
             )
            ])
        res = module.test_unicode_format(1, "xyz")
        assert res == "bla 1 ble xyz\n"

    def test_aswidecharstring(self):
        module = self.import_extension('foo', [
            ("aswidecharstring", "METH_O",
             '''
             PyObject *result;
             Py_ssize_t size;
             wchar_t *buffer;

             buffer = PyUnicode_AsWideCharString(args, &size);
             if (buffer == NULL)
                 return NULL;

             result = PyUnicode_FromWideChar(buffer, size + 1);
             PyMem_Free(buffer);
             if (result == NULL)
                 return NULL;
             return Py_BuildValue("(Nn)", result, size);
             ''')])
        res = module.aswidecharstring("Caf\xe9")
        assert res == ("Caf\xe9\0", 4)

    def test_fromwidechar(self):
        module = self.import_extension('foo', [
            ("truncate", "METH_O",
             '''
             wchar_t buffer[5] = { 0 };

             if (PyUnicode_AsWideChar(args, buffer, 4) == -1)
                 return NULL;

             return PyUnicode_FromWideChar(buffer, -1);
             ''')])
        assert module.truncate("Caf\xe9") == "Caf\xe9"
        assert module.truncate("abcde") == "abcd"
        assert module.truncate("ab") == "ab"

    def test_CompareWithASCIIString(self):
        module = self.import_extension('foo', [
            ("compare", "METH_VARARGS",
             '''
             PyObject *uni;
             const char* s;
             int res;

             if (!PyArg_ParseTuple(args, "Uy", &uni, &s))
                 return NULL;

             res = PyUnicode_CompareWithASCIIString(uni, s);
             return PyLong_FromLong(res);
             ''')])
        assert module.compare("abc", b"abc") == 0
        assert module.compare("abd", b"abc") == 1
        assert module.compare("abb", b"abc") == -1
        assert module.compare("caf\xe9", b"caf\xe9") == 0
        assert module.compare("abc", b"ab") == 1
        assert module.compare("ab\0", b"ab") == 1
        assert module.compare("ab", b"abc") == -1
        assert module.compare("", b"abc") == -1
        assert module.compare("abc", b"") == 1


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

class TestUnicode(BaseApiTest):
    def test_unicodeobject(self, space):
        assert PyUnicode_GET_SIZE(space, space.wrap(u'späm')) == 4
        assert PyUnicode_GetSize(space, space.wrap(u'späm')) == 4
        unichar = rffi.sizeof(Py_UNICODE)
        assert PyUnicode_GET_DATA_SIZE(space, space.wrap(u'späm')) == 4 * unichar

        encoding = rffi.charp2str(PyUnicode_GetDefaultEncoding(space, ))
        w_default_encoding = space.call_function(
            space.sys.get('getdefaultencoding')
        )
        assert encoding == space.unwrap(w_default_encoding)

    def test_AS(self, space):
        word = space.wrap(u'spam')
        array = rffi.cast(rffi.CWCHARP, PyUnicode_AsUnicode(space, word))
        array2 = PyUnicode_AsUnicode(space, word)
        for (i, char) in enumerate(space.unwrap(word)):
            assert array[i] == char
            assert array2[i] == char
        with raises_w(space, TypeError):
            PyUnicode_AsUnicode(space, space.newbytes('spam'))

        utf_8 = rffi.str2charp('utf-8')
        encoded = PyUnicode_AsEncodedString(space, space.wrap(u'späm'),
                                                utf_8, None)
        assert space.unwrap(encoded) == 'sp\xc3\xa4m'
        encoded_obj = PyUnicode_AsEncodedObject(space, space.wrap(u'späm'),
                                                utf_8, None)
        assert space.eq_w(encoded, encoded_obj)
        with raises_w(space, TypeError):
            PyUnicode_AsEncodedString(
               space, space.newtuple([1, 2, 3]), None, None)
        with raises_w(space, TypeError):
            PyUnicode_AsEncodedString(space, space.newbytes(''), None, None)
        ascii = rffi.str2charp('ascii')
        replace = rffi.str2charp('replace')
        encoded = PyUnicode_AsEncodedString(space, space.wrap(u'späm'),
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

    def test_internfromstring(self, space):
        with rffi.scoped_str2charp('foo') as s:
            w_res = PyUnicode_InternFromString(space, s)
            assert space.unwrap(w_res) == u'foo'
            w_res2 = PyUnicode_InternFromString(space, s)
            assert w_res is w_res2

    def test_unicode_resize(self, space):
        py_uni = new_empty_unicode(space, 10)
        ar = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        buf = get_wbuffer(py_uni)
        buf[0] = u'a'
        buf[1] = u'b'
        buf[2] = u'c'
        ar[0] = rffi.cast(PyObject, py_uni)
        PyUnicode_Resize(space, ar, 3)
        py_uni = rffi.cast(PyUnicodeObject, ar[0])
        assert get_wsize(py_uni) == 3
        assert get_wbuffer(py_uni)[1] == u'b'
        assert get_wbuffer(py_uni)[3] == u'\x00'
        # the same for growing
        ar[0] = rffi.cast(PyObject, py_uni)
        PyUnicode_Resize(space, ar, 10)
        py_uni = rffi.cast(PyUnicodeObject, ar[0])
        assert get_wsize(py_uni) == 10
        assert get_wbuffer(py_uni)[1] == 'b'
        assert get_wbuffer(py_uni)[10] == '\x00'
        Py_DecRef(space, ar[0])
        lltype.free(ar, flavor='raw')

    def test_AsUTF8String(self, space):
        w_u = space.wrap(u'sp\x09m')
        w_res = PyUnicode_AsUTF8String(space, w_u)
        assert space.type(w_res) is space.w_str
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

    def test_encode_fsdefault(self, space):
        w_u = space.wrap(u'späm')
        w_s = PyUnicode_EncodeFSDefault(space, w_u)
        if w_s is None:
            PyErr_Clear(space)
            py.test.skip("Requires a unicode-aware fsencoding")
        with rffi.scoped_str2charp(space.str_w(w_s)) as encoded:
            w_decoded = PyUnicode_DecodeFSDefaultAndSize(space, encoded, space.len_w(w_s))
            assert space.eq_w(w_decoded, w_u)
            w_decoded = PyUnicode_DecodeFSDefault(space, encoded)
            assert space.eq_w(w_decoded, w_u)

    def test_fsconverter(self, space):
        # Input is bytes
        w_input = space.newbytes("test")
        with lltype.scoped_alloc(PyObjectP.TO, 1) as result:
            # Decoder
            ret = PyUnicode_FSDecoder(space, w_input, result)
            assert ret == Py_CLEANUP_SUPPORTED
            assert space.isinstance_w(from_ref(space, result[0]), space.w_unicode)
            assert PyUnicode_FSDecoder(space, None, result) == 1
            # Converter
            ret = PyUnicode_FSConverter(space, w_input, result)
            assert ret == Py_CLEANUP_SUPPORTED
            assert space.eq_w(from_ref(space, result[0]), w_input)
            assert PyUnicode_FSDecoder(space, None, result) == 1
        # Input is unicode
        w_input = space.wrap("test")
        with lltype.scoped_alloc(PyObjectP.TO, 1) as result:
            # Decoder
            ret = PyUnicode_FSDecoder(space, w_input, result)
            assert ret == Py_CLEANUP_SUPPORTED
            assert space.eq_w(from_ref(space, result[0]), w_input)
            assert PyUnicode_FSDecoder(space, None, result) == 1
            # Converter
            ret = PyUnicode_FSConverter(space, w_input, result)
            assert ret == Py_CLEANUP_SUPPORTED
            assert space.isinstance_w(from_ref(space, result[0]), space.w_bytes)
            assert PyUnicode_FSDecoder(space, None, result) == 1

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

    def test_transform_decimal(self, space):
        def transform_decimal(s):
            with rffi.scoped_unicode2wcharp(s) as u:
                return space.unwrap(
                    PyUnicode_TransformDecimalToASCII(space, u, len(s)))
        assert isinstance(transform_decimal(u'123'), unicode)
        assert transform_decimal(u'123') == u'123'
        assert transform_decimal(u'\u0663.\u0661\u0664') == u'3.14'
        assert transform_decimal(u"\N{EM SPACE}3.14\N{EN SPACE}") == (
            u"\N{EM SPACE}3.14\N{EN SPACE}")
        assert transform_decimal(u'123\u20ac') == u'123\u20ac'

    def test_fromobject(self, space):
        w_u = space.wrap(u'a')
        assert PyUnicode_FromObject(space, w_u) is w_u
        assert space.unwrap(
            PyUnicode_FromObject(space, space.newbytes('test'))) == "b'test'"

    def test_decode(self, space):
        b_text = rffi.str2charp('caf\x82xx')
        b_encoding = rffi.str2charp('cp437')
        assert space.unwrap(
            PyUnicode_Decode(space, b_text, 4, b_encoding, None)) == u'caf\xe9'

        w_text = PyUnicode_FromEncodedObject(space, space.newbytes("test"), b_encoding, None)
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
        w_str = PyUnicode_EncodeMBCS(space, wbuf, 4, None)
        rffi.free_wcharp(wbuf)
        assert space.type(w_str) is space.w_str
        assert space.str_w(w_str) == "abc?"

    def test_escape(self, space):
        def test(ustr):
            w_ustr = space.wrap(ustr.decode('Unicode-Escape'))
            result = PyUnicode_AsUnicodeEscapeString(space, w_ustr)
            assert space.eq_w(space.newbytes(ustr), result)

        test('\\u674f\\u7f8e')
        test('\\u0105\\u0107\\u017c\\u017a')
        test('El Ni\\xf1o')

    def test_ascii(self, space):
        ustr = "abcdef"
        w_ustr = space.wrap(ustr.decode("ascii"))
        result = PyUnicode_AsASCIIString(space, w_ustr)
        assert space.eq_w(space.newbytes(ustr), result)
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
                              space.newbytes("abcd"))

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
                              space.newbytes("ab"))

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

        x_chunk = PyUnicode_AsUnicode(space, w_x)
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
        assert space.eq_w(space.newbytes("abcdefg"), w_s)
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
        assert space.eq_w(space.newbytes("abcdefg"), w_s)
        rffi.free_wcharp(data)

        ustr = "abcdef"
        w_ustr = space.wrap(ustr.decode("ascii"))
        result = PyUnicode_AsLatin1String(space, w_ustr)
        assert space.eq_w(space.newbytes(ustr), result)

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
        assert "['a', 'b', 'c', 'd']" == space.unwrap(space.repr(
                PyUnicode_Split(space, w_str, space.wrap('\n'), -1)))
        assert r"['a', 'b', 'c\nd']" == space.unwrap(space.repr(
                PyUnicode_Split(space, w_str, space.wrap('\n'), 2)))
        assert r"['a', 'b', 'c d']" == space.unwrap(space.repr(
                PyUnicode_Split(space, space.wrap(u'a\nb  c d'), None, 2)))
        assert "['a', 'b', 'c', 'd']" == space.unwrap(space.repr(
                PyUnicode_Splitlines(space, w_str, 0)))
        assert r"['a\n', 'b\n', 'c\n', 'd']" == space.unwrap(space.repr(
                PyUnicode_Splitlines(space, w_str, 1)))

    def test_Ready(self, space):
        w_str = space.wrap(u'abc')  # ASCII
        py_str = as_pyobj(space, w_str)
        assert get_kind(py_str) == 0
        _PyUnicode_Ready(space, w_str)
        assert get_kind(py_str) == 1
        assert get_ascii(py_str) == 1

        w_str = space.wrap(u'café')  # latin1
        py_str = as_pyobj(space, w_str)
        assert get_kind(py_str) == 0
        _PyUnicode_Ready(space, w_str)
        assert get_kind(py_str) == 1
        assert get_ascii(py_str) == 0

        w_str = space.wrap(u'Росси́я')  # UCS2
        py_str = as_pyobj(space, w_str)
        assert get_kind(py_str) == 0
        _PyUnicode_Ready(space, w_str)
        assert get_kind(py_str) == 2
        assert get_ascii(py_str) == 0

        w_str = space.wrap(u'***\U0001f4a9***')  # UCS4
        py_str = as_pyobj(space, w_str)
        assert get_kind(py_str) == 0
        _PyUnicode_Ready(space, w_str)
        assert get_kind(py_str) == 4
        assert get_ascii(py_str) == 0
