# encoding: utf-8
import pytest
from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.interpreter.error import OperationError
from pypy.module.cpyext.test.test_api import BaseApiTest, raises_w
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.bytesobject import (
    new_empty_str, PyBytesObject, _PyString_Resize, PyString_Concat,
    PyString_ConcatAndDel, PyString_Format, PyString_InternFromString,
    PyString_AsEncodedObject, PyString_AsDecodedObject, _PyString_Eq,
    _PyString_Join)
from pypy.module.cpyext.api import PyObjectP, PyObject, Py_ssize_tP, generic_cpy_call
from pypy.module.cpyext.pyobject import Py_DecRef, from_ref, make_ref
from pypy.module.cpyext.object import PyObject_AsCharBuffer


class AppTestBytesObject(AppTestCpythonExtensionBase):
    def test_bytesobject(self):
        module = self.import_extension('foo', [
            ("get_hello1", "METH_NOARGS",
             """
                 return PyBytes_FromStringAndSize(
                     "Hello world<should not be included>", 11);
             """),
            ("get_hello2", "METH_NOARGS",
             """
                 return PyBytes_FromString("Hello world");
             """),
            ("test_Size", "METH_NOARGS",
             """
                 PyObject* s = PyBytes_FromString("Hello world");
                 int result = PyBytes_Size(s);

                 Py_DECREF(s);
                 return PyLong_FromLong(result);
             """),
            ("test_Size_exception", "METH_NOARGS",
             """
                 PyObject* f = PyFloat_FromDouble(1.0);
                 PyBytes_Size(f);

                 Py_DECREF(f);
                 return NULL;
             """),
             ("test_is_bytes", "METH_VARARGS",
             """
                return PyBool_FromLong(PyBytes_Check(PyTuple_GetItem(args, 0)));
             """)], prologue='#include <stdlib.h>')
        assert module.get_hello1() == b'Hello world'
        assert module.get_hello2() == b'Hello world'
        assert module.test_Size() == 11
        raises(TypeError, module.test_Size_exception)

        assert module.test_is_bytes(b"")
        assert not module.test_is_bytes(())

    def test_bytes_buffer_init(self):
        module = self.import_extension('foo', [
            ("getbytes", "METH_NOARGS",
             """
                 PyObject *s, *t;
                 char* c;

                 s = PyBytes_FromStringAndSize(NULL, 4);
                 if (s == NULL)
                    return NULL;
                 t = PyBytes_FromStringAndSize(NULL, 3);
                 if (t == NULL)
                    return NULL;
                 Py_DECREF(t);
                 c = PyBytes_AS_STRING(s);
                 c[0] = 'a';
                 c[1] = 'b';
                 c[2] = 0;
                 c[3] = 'c';
                 return s;
             """),
            ])
        s = module.getbytes()
        assert len(s) == 4
        assert s == b'ab\x00c'

    def test_bytes_tp_alloc(self):
        module = self.import_extension('foo', [
            ("tpalloc", "METH_NOARGS",
             """
                PyObject *base;
                PyTypeObject * type;
                PyBytesObject *obj;
                base = PyBytes_FromString("test");
                if (PyBytes_GET_SIZE(base) != 4)
                    return PyLong_FromLong(-PyBytes_GET_SIZE(base));
                type = base->ob_type;
                if (type->tp_itemsize != 1)
                    return PyLong_FromLong(type->tp_itemsize);
                obj = (PyBytesObject*)type->tp_alloc(type, 10);
                if (PyBytes_GET_SIZE(obj) != 10)
                    return PyLong_FromLong(PyBytes_GET_SIZE(obj));
                /* cannot work, there is only RO access
                memcpy(PyBytes_AS_STRING(obj), "works", 6); */
                Py_INCREF(obj);
                return (PyObject*)obj;
             """),
            ('alloc_rw', "METH_NOARGS",
             '''
                PyObject *obj = _PyObject_NewVar(&PyBytes_Type, 10);
                memcpy(PyBytes_AS_STRING(obj), "works", 6);
                return (PyObject*)obj;
             '''),
            ])
        s = module.alloc_rw()
        assert s[:6] == b'works\0'  # s[6:10] contains random garbage
        s = module.tpalloc()
        assert s == b'\x00' * 10

    def test_AsString(self):
        module = self.import_extension('foo', [
            ("getbytes", "METH_NOARGS",
             """
                 char *c;
                 PyObject* s2, *s1 = PyBytes_FromStringAndSize("test", 4);
                 c = PyBytes_AsString(s1);
                 s2 = PyBytes_FromStringAndSize(c, 4);
                 Py_DECREF(s1);
                 return s2;
             """),
            ])
        s = module.getbytes()
        assert s == b'test'

    def test_manipulations(self):
        module = self.import_extension('foo', [
            ("bytes_as_string", "METH_VARARGS",
             '''
             return PyBytes_FromStringAndSize(PyBytes_AsString(
                       PyTuple_GetItem(args, 0)), 4);
             '''
            ),
            ("concat", "METH_VARARGS",
             """
                PyObject ** v;
                PyObject * left = PyTuple_GetItem(args, 0);
                Py_INCREF(left);    /* the reference will be stolen! */
                v = &left;
                PyBytes_Concat(v, PyTuple_GetItem(args, 1));
                return *v;
             """)])
        assert module.bytes_as_string(b"huheduwe") == b"huhe"
        ret = module.concat(b'abc', b'def')
        assert ret == b'abcdef'
        ret = module.concat('abc', u'def')
        assert not isinstance(ret, str)
        assert isinstance(ret, unicode)
        assert ret == 'abcdef'

    def test_py_bytes_as_string_None(self):
        module = self.import_extension('foo', [
            ("string_None", "METH_VARARGS",
             '''
             if (PyBytes_AsString(Py_None)) {
                Py_RETURN_NONE;
             }
             return NULL;
             '''
            )])
        raises(TypeError, module.string_None)

    def test_AsStringAndSize(self):
        module = self.import_extension('foo', [
            ("getbytes", "METH_NOARGS",
             """
                 PyObject* s1 = PyBytes_FromStringAndSize("te\\0st", 5);
                 char *buf;
                 Py_ssize_t len;
                 if (PyBytes_AsStringAndSize(s1, &buf, &len) < 0)
                     return NULL;
                 if (len != 5) {
                     PyErr_SetString(PyExc_AssertionError, "Bad Length");
                     return NULL;
                 }
                 if (PyBytes_AsStringAndSize(s1, &buf, NULL) >= 0) {
                     PyErr_SetString(PyExc_AssertionError, "Should Have failed");
                     return NULL;
                 }
                 PyErr_Clear();
                 Py_DECREF(s1);
                 Py_INCREF(Py_None);
                 return Py_None;
             """),
            ("c_only", "METH_NOARGS",
            """
                int ret;
                char * buf2;
                PyObject * obj = PyBytes_FromStringAndSize(NULL, 1024);
                if (!obj)
                    return NULL;
                buf2 = PyBytes_AsString(obj);
                if (!buf2)
                    return NULL;
                /* buf should not have been forced, issue #2395 */
                ret = _PyBytes_Resize(&obj, 512);
                if (ret < 0)
                    return NULL;
                 Py_DECREF(obj);
                 Py_INCREF(Py_None);
                 return Py_None;
            """),
            ])
        module.getbytes()
        module.c_only()

    def test_py_string_as_string_Unicode(self):
        module = self.import_extension('foo', [
            ("getstring_unicode", "METH_NOARGS",
             """
                 Py_UNICODE chars[] = {'t', 'e', 's', 't'};
                 PyObject* u1 = PyUnicode_FromUnicode(chars, 4);
                 char *buf;
                 buf = PyString_AsString(u1);
                 if (buf == NULL)
                     return NULL;
                 if (buf[3] != 't') {
                     PyErr_SetString(PyExc_AssertionError, "Bad conversion");
                     return NULL;
                 }
                 Py_DECREF(u1);
                 Py_INCREF(Py_None);
                 return Py_None;
             """),
            ("getstringandsize_unicode", "METH_NOARGS",
             """
                 Py_UNICODE chars[] = {'t', 'e', 's', 't'};
                 PyObject* u1 = PyUnicode_FromUnicode(chars, 4);
                 char *buf;
                 Py_ssize_t len;
                 if (PyString_AsStringAndSize(u1, &buf, &len) < 0)
                     return NULL;
                 if (len != 4) {
                     PyErr_SetString(PyExc_AssertionError, "Bad Length");
                     return NULL;
                 }
                 Py_DECREF(u1);
                 Py_INCREF(Py_None);
                 return Py_None;
             """),
            ])
        module.getstring_unicode()
        module.getstringandsize_unicode()

    def test_format_v(self):
        module = self.import_extension('foo', [
            ("test_string_format_v", "METH_VARARGS",
             '''
                 return helper("bla %d ble %s\\n",
                        PyInt_AsLong(PyTuple_GetItem(args, 0)),
                        PyString_AsString(PyTuple_GetItem(args, 1)));
             '''
             )
            ], prologue='''
            PyObject* helper(char* fmt, ...)
            {
              va_list va;
              PyObject* res;
              va_start(va, fmt);
              res = PyString_FromFormatV(fmt, va);
              va_end(va);
              return res;
            }
            ''')
        res = module.test_string_format_v(1, "xyz")
        assert res == "bla 1 ble xyz\n"

    def test_format(self):
        module = self.import_extension('foo', [
            ("test_string_format", "METH_VARARGS",
             '''
                 return PyString_FromFormat("bla %d ble %s\\n",
                        PyInt_AsLong(PyTuple_GetItem(args, 0)),
                        PyString_AsString(PyTuple_GetItem(args, 1)));
             '''
             )
            ])
        res = module.test_string_format(1, "xyz")
        assert res == "bla 1 ble xyz\n"

    def test_intern_inplace(self):
        module = self.import_extension('foo', [
            ("test_intern_inplace", "METH_O",
             '''
                 PyObject *s = args;
                 Py_INCREF(s);
                 PyString_InternInPlace(&s);
                 if (((PyBytesObject*)s)->ob_sstate == SSTATE_NOT_INTERNED)
                 {
                    Py_DECREF(s);
                    s = PyString_FromString("interned error");
                 }
                 return s;
             '''
             )
            ])
        # This does not test much, but at least the refcounts are checked.
        assert module.test_intern_inplace('s') == 's'

    def test_bytes_macros(self):
        """The PyString_* macros cast, and calls expecting that build."""
        module = self.import_extension('foo', [
             ("test_macro_invocations", "METH_NOARGS",
             """
                PyObject* o = PyString_FromString("");
                PyBytesObject* u = (PyBytesObject*)o;

                PyString_GET_SIZE(u);
                PyString_GET_SIZE(o);

                PyString_AS_STRING(o);
                PyString_AS_STRING(u);

                return o;
             """)])
        assert module.test_macro_invocations() == ''

    def test_hash_and_state(self):
        module = self.import_extension('foo', [
            ("test_hash", "METH_VARARGS",
             '''
                PyObject* obj = (PyTuple_GetItem(args, 0));
                long hash = ((PyBytesObject*)obj)->ob_shash;
                return PyLong_FromLong(hash);
             '''
             ),
            ("test_sstate", "METH_NOARGS",
             '''
                PyObject *s = PyString_FromString("xyz");
                /*int sstate = ((PyBytesObject*)s)->ob_sstate;
                printf("sstate now %d\\n", sstate);*/
                PyString_InternInPlace(&s);
                /*sstate = ((PyBytesObject*)s)->ob_sstate;
                printf("sstate now %d\\n", sstate);*/
                Py_DECREF(s);
                return PyBool_FromLong(1);
             '''),
            ], prologue='#include <stdlib.h>')
        res = module.test_hash("xyz")
        assert res == hash('xyz')
        # doesn't really test, but if printf is enabled will prove sstate
        assert module.test_sstate()

    def test_subclass(self):
        # taken from PyStringArrType_Type in numpy's scalartypes.c.src
        module = self.import_extension('bar', [
            ("newsubstr", "METH_O",
             """
                PyObject * obj;
                char * data;
                int len;

                data = PyString_AS_STRING(args);
                len = PyString_GET_SIZE(args);
                if (data == NULL || len < 1)
                    Py_RETURN_NONE;
                obj = PyArray_Scalar(data, len);
                return obj;
             """),
            ], prologue="""
                #include <Python.h>
                PyTypeObject PyStringArrType_Type = {
                    PyObject_HEAD_INIT(NULL)
                    0,                            /* ob_size */
                    "bar.string_",                /* tp_name*/
                    sizeof(PyBytesObject), /* tp_basicsize*/
                    0                             /* tp_itemsize */
                    };

                    static PyObject *
                    stringtype_repr(PyObject *self)
                    {
                        const char *dptr, *ip;
                        int len;
                        PyObject *new;

                        ip = dptr = PyString_AS_STRING(self);
                        len = PyString_GET_SIZE(self);
                        dptr += len-1;
                        while(len > 0 && *dptr-- == 0) {
                            len--;
                        }
                        new = PyString_FromStringAndSize(ip, len);
                        if (new == NULL) {
                            return PyString_FromString("");
                        }
                        return new;
                    }

                    static PyObject *
                    stringtype_str(PyObject *self)
                    {
                        const char *dptr, *ip;
                        int len;
                        PyObject *new;

                        ip = dptr = PyString_AS_STRING(self);
                        len = PyString_GET_SIZE(self);
                        dptr += len-1;
                        while(len > 0 && *dptr-- == 0) {
                            len--;
                        }
                        new = PyString_FromStringAndSize(ip, len);
                        if (new == NULL) {
                            return PyString_FromString("");
                        }
                        return new;
                    }

                    PyObject *
                    PyArray_Scalar(char *data, int n)
                    {
                        PyTypeObject *type = &PyStringArrType_Type;
                        PyObject *obj;
                        void *destptr;
                        int itemsize = n;
                        obj = type->tp_alloc(type, itemsize);
                        if (obj == NULL) {
                            return NULL;
                        }
                        destptr = PyString_AS_STRING(obj);
                        ((PyBytesObject *)obj)->ob_shash = -1;
                        memcpy(destptr, data, itemsize);
                        return obj;
                    }
            """, more_init = '''
                PyStringArrType_Type.tp_alloc = NULL;
                PyStringArrType_Type.tp_free = NULL;

                PyStringArrType_Type.tp_repr = stringtype_repr;
                PyStringArrType_Type.tp_str = stringtype_str;
                PyStringArrType_Type.tp_flags = Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE;
                PyStringArrType_Type.tp_itemsize = sizeof(char);
                PyStringArrType_Type.tp_base = &PyString_Type;
                if (PyType_Ready(&PyStringArrType_Type) < 0) INITERROR;
            ''')

        a = module.newsubstr('abc')
        assert type(a).__name__ == 'string_'
        assert a == 'abc'

class TestBytes(BaseApiTest):
    def test_bytes_resize(self, space):
        py_str = new_empty_str(space, 10)
        ar = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        py_str.c_ob_sval[0] = 'a'
        py_str.c_ob_sval[1] = 'b'
        py_str.c_ob_sval[2] = 'c'
        ar[0] = rffi.cast(PyObject, py_str)
        _PyString_Resize(space, ar, 3)
        py_str = rffi.cast(PyBytesObject, ar[0])
        assert py_str.c_ob_size == 3
        assert py_str.c_ob_sval[1] == 'b'
        assert py_str.c_ob_sval[3] == '\x00'
        # the same for growing
        ar[0] = rffi.cast(PyObject, py_str)
        _PyString_Resize(space, ar, 10)
        py_str = rffi.cast(PyBytesObject, ar[0])
        assert py_str.c_ob_size == 10
        assert py_str.c_ob_sval[1] == 'b'
        assert py_str.c_ob_sval[10] == '\x00'
        Py_DecRef(space, ar[0])
        lltype.free(ar, flavor='raw')

    def test_string_buffer(self, space):
        py_str = new_empty_str(space, 10)
        c_buf = py_str.c_ob_type.c_tp_as_buffer
        assert c_buf
        py_obj = rffi.cast(PyObject, py_str)
        assert generic_cpy_call(space, c_buf.c_bf_getsegcount,
                                py_obj, lltype.nullptr(Py_ssize_tP.TO)) == 1
        ref = lltype.malloc(Py_ssize_tP.TO, 1, flavor='raw')
        assert generic_cpy_call(space, c_buf.c_bf_getsegcount,
                                py_obj, ref) == 1
        assert ref[0] == 10
        lltype.free(ref, flavor='raw')
        ref = lltype.malloc(rffi.VOIDPP.TO, 1, flavor='raw')
        assert generic_cpy_call(space, c_buf.c_bf_getreadbuffer,
                                py_obj, 0, ref) == 10
        lltype.free(ref, flavor='raw')
        Py_DecRef(space, py_obj)

    def test_Concat(self, space):
        ref = make_ref(space, space.wrap('abc'))
        ptr = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        ptr[0] = ref
        prev_refcnt = ref.c_ob_refcnt
        PyString_Concat(space, ptr, space.wrap('def'))
        assert ref.c_ob_refcnt == prev_refcnt - 1
        assert space.str_w(from_ref(space, ptr[0])) == 'abcdef'
        with pytest.raises(OperationError):
            PyString_Concat(space, ptr, space.w_None)
        assert not ptr[0]
        ptr[0] = lltype.nullptr(PyObject.TO)
        PyString_Concat(space, ptr, space.wrap('def')) # should not crash
        lltype.free(ptr, flavor='raw')

    def test_ConcatAndDel(self, space):
        ref1 = make_ref(space, space.wrap('abc'))
        ref2 = make_ref(space, space.wrap('def'))
        ptr = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        ptr[0] = ref1
        prev_refcnf = ref2.c_ob_refcnt
        PyString_ConcatAndDel(space, ptr, ref2)
        assert space.str_w(from_ref(space, ptr[0])) == 'abcdef'
        assert ref2.c_ob_refcnt == prev_refcnf - 1
        Py_DecRef(space, ptr[0])
        ptr[0] = lltype.nullptr(PyObject.TO)
        ref2 = make_ref(space, space.wrap('foo'))
        prev_refcnf = ref2.c_ob_refcnt
        PyString_ConcatAndDel(space, ptr, ref2) # should not crash
        assert ref2.c_ob_refcnt == prev_refcnf - 1
        lltype.free(ptr, flavor='raw')

    def test_format(self, space):
        assert "1 2" == space.unwrap(
            PyString_Format(space, space.wrap('%s %d'), space.wrap((1, 2))))

    def test_asbuffer(self, space):
        bufp = lltype.malloc(rffi.CCHARPP.TO, 1, flavor='raw')
        lenp = lltype.malloc(Py_ssize_tP.TO, 1, flavor='raw')

        w_text = space.wrap("text")
        ref = make_ref(space, w_text)
        prev_refcnt = ref.c_ob_refcnt
        assert PyObject_AsCharBuffer(space, ref, bufp, lenp) == 0
        assert ref.c_ob_refcnt == prev_refcnt
        assert lenp[0] == 4
        assert rffi.charp2str(bufp[0]) == 'text'
        lltype.free(bufp, flavor='raw')
        lltype.free(lenp, flavor='raw')
        Py_DecRef(space, ref)

    def test_intern(self, space):
        buf = rffi.str2charp("test")
        w_s1 = PyString_InternFromString(space, buf)
        w_s2 = PyString_InternFromString(space, buf)
        rffi.free_charp(buf)
        assert w_s1 is w_s2

    def test_AsEncodedObject(self, space):
        ptr = space.wrap('abc')

        errors = rffi.str2charp("strict")

        encoding = rffi.str2charp("hex")
        res = PyString_AsEncodedObject(space, ptr, encoding, errors)
        assert space.unwrap(res) == "616263"

        res = PyString_AsEncodedObject(space,
            ptr, encoding, lltype.nullptr(rffi.CCHARP.TO))
        assert space.unwrap(res) == "616263"
        rffi.free_charp(encoding)

        encoding = rffi.str2charp("unknown_encoding")
        with raises_w(space, LookupError):
            PyString_AsEncodedObject(space, ptr, encoding, errors)
        rffi.free_charp(encoding)

        rffi.free_charp(errors)

        NULL = lltype.nullptr(rffi.CCHARP.TO)
        res = PyString_AsEncodedObject(space, ptr, NULL, NULL)
        assert space.unwrap(res) == "abc"
        with raises_w(space, TypeError):
            PyString_AsEncodedObject(space, space.wrap(2), NULL, NULL)

    def test_AsDecodedObject(self, space):
        w_str = space.wrap('caf\xe9')
        encoding = rffi.str2charp("latin-1")
        w_res = PyString_AsDecodedObject(space, w_str, encoding, None)
        rffi.free_charp(encoding)
        assert space.unwrap(w_res) == u"caf\xe9"

    def test_eq(self, space):
        assert 1 == _PyString_Eq(
            space, space.wrap("hello"), space.wrap("hello"))
        assert 0 == _PyString_Eq(
            space, space.wrap("hello"), space.wrap("world"))

    def test_join(self, space):
        w_sep = space.wrap('<sep>')
        w_seq = space.wrap(['a', 'b'])
        w_joined = _PyString_Join(space, w_sep, w_seq)
        assert space.unwrap(w_joined) == 'a<sep>b'
