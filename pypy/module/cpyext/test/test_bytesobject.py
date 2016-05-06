# encoding: utf-8
from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.bytesobject import new_empty_str, PyStringObject
from pypy.module.cpyext.api import PyObjectP, PyObject, Py_ssize_tP, generic_cpy_call
from pypy.module.cpyext.pyobject import Py_DecRef, from_ref, make_ref
from pypy.module.cpyext.typeobjectdefs import PyTypeObjectPtr

import py
import sys

class AppTestStringObject(AppTestCpythonExtensionBase):
    def test_stringobject(self):
        module = self.import_extension('foo', [
            ("get_hello1", "METH_NOARGS",
             """
                 return PyString_FromStringAndSize(
                     "Hello world<should not be included>", 11);
             """),
            ("get_hello2", "METH_NOARGS",
             """
                 return PyString_FromString("Hello world");
             """),
            ("test_Size", "METH_NOARGS",
             """
                 PyObject* s = PyString_FromString("Hello world");
                 int result = 0;
                 size_t expected_size;

                 if(PyString_Size(s) == 11) {
                     result = 1;
                 }
                 #ifdef PYPY_VERSION
                    expected_size = sizeof(void*)*7;
                 #elif defined Py_DEBUG
                    expected_size = 53;
                 #else
                    expected_size = 37;
                 #endif
                 if(s->ob_type->tp_basicsize != expected_size)
                 {
                     printf("tp_basicsize==%ld\\n", s->ob_type->tp_basicsize); 
                     result = 0;
                 }
                 Py_DECREF(s);
                 return PyBool_FromLong(result);
             """),
            ("test_Size_exception", "METH_NOARGS",
             """
                 PyObject* f = PyFloat_FromDouble(1.0);
                 Py_ssize_t size = PyString_Size(f);

                 Py_DECREF(f);
                 return NULL;
             """),
             ("test_is_string", "METH_VARARGS",
             """
                return PyBool_FromLong(PyString_Check(PyTuple_GetItem(args, 0)));
             """)], prologue='#include <stdlib.h>')
        assert module.get_hello1() == 'Hello world'
        assert module.get_hello2() == 'Hello world'
        assert module.test_Size()
        raises(TypeError, module.test_Size_exception)

        assert module.test_is_string("")
        assert not module.test_is_string(())

    def test_string_buffer_init(self):
        module = self.import_extension('foo', [
            ("getstring", "METH_NOARGS",
             """
                 PyObject *s, *t;
                 char* c;
                 Py_ssize_t len;

                 s = PyString_FromStringAndSize(NULL, 4);
                 if (s == NULL)
                    return NULL;
                 t = PyString_FromStringAndSize(NULL, 3);
                 if (t == NULL)
                    return NULL;
                 Py_DECREF(t);
                 c = PyString_AsString(s);
                 c[0] = 'a';
                 c[1] = 'b';
                 c[2] = 0;
                 c[3] = 'c';
                 return s;
             """),
            ])
        s = module.getstring()
        assert len(s) == 4
        assert s == 'ab\x00c'

    def test_string_tp_alloc(self):
        module = self.import_extension('foo', [
            ("tpalloc", "METH_NOARGS",
             """
                PyObject *base;
                PyTypeObject * type;
                PyStringObject *obj;
                char * p_str;
                base = PyString_FromString("test");
                if (PyString_GET_SIZE(base) != 4)
                    return PyLong_FromLong(-PyString_GET_SIZE(base));
                type = base->ob_type;
                if (type->tp_itemsize != 1)
                    return PyLong_FromLong(type->tp_itemsize);
                obj = (PyStringObject*)type->tp_alloc(type, 10);
                if (PyString_GET_SIZE(obj) != 10)
                    return PyLong_FromLong(PyString_GET_SIZE(obj));
                /* cannot work, there is only RO access
                memcpy(PyString_AS_STRING(obj), "works", 6); */
                Py_INCREF(obj);
                return (PyObject*)obj;
             """),
            ])
        s = module.tpalloc()
        assert s == '\x00' * 10

    def test_AsString(self):
        module = self.import_extension('foo', [
            ("getstring", "METH_NOARGS",
             """
                 PyObject* s1 = PyString_FromStringAndSize("test", 4);
                 char* c = PyString_AsString(s1);
                 PyObject* s2 = PyString_FromStringAndSize(c, 4);
                 Py_DECREF(s1);
                 return s2;
             """),
            ])
        s = module.getstring()
        assert s == 'test'

    def test_manipulations(self):
        module = self.import_extension('foo', [
            ("string_as_string", "METH_VARARGS",
             '''
             return PyString_FromStringAndSize(PyString_AsString(
                       PyTuple_GetItem(args, 0)), 4);
             '''
            ),
            ("concat", "METH_VARARGS",
             """
                PyObject ** v;
                PyObject * left = PyTuple_GetItem(args, 0);
                Py_INCREF(left);    /* the reference will be stolen! */
                v = &left;
                PyString_Concat(v, PyTuple_GetItem(args, 1));
                return *v;
             """)])
        assert module.string_as_string("huheduwe") == "huhe"
        ret = module.concat('abc', 'def')
        assert ret == 'abcdef'
        ret = module.concat('abc', u'def')
        assert not isinstance(ret, str)
        assert isinstance(ret, unicode)
        assert ret == 'abcdef'

    def test_py_string_as_string_None(self):
        module = self.import_extension('foo', [
            ("string_None", "METH_VARARGS",
             '''
             if (PyString_AsString(Py_None)) {
                Py_RETURN_NONE;
             }
             return NULL;
             '''
            )])
        raises(TypeError, module.string_None)

    def test_AsStringAndSize(self):
        module = self.import_extension('foo', [
            ("getstring", "METH_NOARGS",
             """
                 PyObject* s1 = PyString_FromStringAndSize("te\\0st", 5);
                 char *buf;
                 Py_ssize_t len;
                 if (PyString_AsStringAndSize(s1, &buf, &len) < 0)
                     return NULL;
                 if (len != 5) {
                     PyErr_SetString(PyExc_AssertionError, "Bad Length");
                     return NULL;
                 }
                 if (PyString_AsStringAndSize(s1, &buf, NULL) >= 0) {
                     PyErr_SetString(PyExc_AssertionError, "Should Have failed");
                     return NULL;
                 }
                 PyErr_Clear();
                 Py_DECREF(s1);
                 Py_INCREF(Py_None);
                 return Py_None;
             """),
            ])
        module.getstring()

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
                 if (((PyStringObject*)s)->ob_sstate == SSTATE_NOT_INTERNED)
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

    def test_hash_and_state(self):
        module = self.import_extension('foo', [
            ("test_hash", "METH_VARARGS",
             '''
                PyObject* obj = (PyTuple_GetItem(args, 0));
                long hash = ((PyStringObject*)obj)->ob_shash;
                return PyLong_FromLong(hash);  
             '''
             ),
            ("test_sstate", "METH_NOARGS",
             '''
                PyObject *s = PyString_FromString("xyz");
                int sstate = ((PyStringObject*)s)->ob_sstate;
                /*printf("sstate now %d\\n", sstate);*/
                PyString_InternInPlace(&s);
                sstate = ((PyStringObject*)s)->ob_sstate;
                /*printf("sstate now %d\\n", sstate);*/
                Py_DECREF(s);
                return PyBool_FromLong(1);
             '''),
            ], prologue='#include <stdlib.h>')
        res = module.test_hash("xyz")
        assert res == hash('xyz')
        # doesn't really test, but if printf is enabled will prove sstate
        assert module.test_sstate()


class TestString(BaseApiTest):
    def test_string_resize(self, space, api):
        py_str = new_empty_str(space, 10)
        ar = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        py_str.c_buffer[0] = 'a'
        py_str.c_buffer[1] = 'b'
        py_str.c_buffer[2] = 'c'
        ar[0] = rffi.cast(PyObject, py_str)
        api._PyString_Resize(ar, 3)
        py_str = rffi.cast(PyStringObject, ar[0])
        assert py_str.c_ob_size == 3
        assert py_str.c_buffer[1] == 'b'
        assert py_str.c_buffer[3] == '\x00'
        # the same for growing
        ar[0] = rffi.cast(PyObject, py_str)
        api._PyString_Resize(ar, 10)
        py_str = rffi.cast(PyStringObject, ar[0])
        assert py_str.c_ob_size == 10
        assert py_str.c_buffer[1] == 'b'
        assert py_str.c_buffer[10] == '\x00'
        Py_DecRef(space, ar[0])
        lltype.free(ar, flavor='raw')

    def test_string_buffer(self, space, api):
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

    def test_Concat(self, space, api):
        ref = make_ref(space, space.wrap('abc'))
        ptr = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        ptr[0] = ref
        prev_refcnt = ref.c_ob_refcnt
        api.PyString_Concat(ptr, space.wrap('def'))
        assert ref.c_ob_refcnt == prev_refcnt - 1
        assert space.str_w(from_ref(space, ptr[0])) == 'abcdef'
        api.PyString_Concat(ptr, space.w_None)
        assert not ptr[0]
        api.PyErr_Clear()
        ptr[0] = lltype.nullptr(PyObject.TO)
        api.PyString_Concat(ptr, space.wrap('def')) # should not crash
        lltype.free(ptr, flavor='raw')

    def test_ConcatAndDel(self, space, api):
        ref1 = make_ref(space, space.wrap('abc'))
        ref2 = make_ref(space, space.wrap('def'))
        ptr = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        ptr[0] = ref1
        prev_refcnf = ref2.c_ob_refcnt
        api.PyString_ConcatAndDel(ptr, ref2)
        assert space.str_w(from_ref(space, ptr[0])) == 'abcdef'
        assert ref2.c_ob_refcnt == prev_refcnf - 1
        Py_DecRef(space, ptr[0])
        ptr[0] = lltype.nullptr(PyObject.TO)
        ref2 = make_ref(space, space.wrap('foo'))
        prev_refcnf = ref2.c_ob_refcnt
        api.PyString_ConcatAndDel(ptr, ref2) # should not crash
        assert ref2.c_ob_refcnt == prev_refcnf - 1
        lltype.free(ptr, flavor='raw')

    def test_format(self, space, api):
        assert "1 2" == space.unwrap(
            api.PyString_Format(space.wrap('%s %d'), space.wrap((1, 2))))

    def test_asbuffer(self, space, api):
        bufp = lltype.malloc(rffi.CCHARPP.TO, 1, flavor='raw')
        lenp = lltype.malloc(Py_ssize_tP.TO, 1, flavor='raw')

        w_text = space.wrap("text")
        assert api.PyObject_AsCharBuffer(w_text, bufp, lenp) == 0
        assert lenp[0] == 4
        assert rffi.charp2str(bufp[0]) == 'text'

        lltype.free(bufp, flavor='raw')
        lltype.free(lenp, flavor='raw')

    def test_intern(self, space, api):
        buf = rffi.str2charp("test")
        w_s1 = api.PyString_InternFromString(buf)
        w_s2 = api.PyString_InternFromString(buf)
        rffi.free_charp(buf)
        assert w_s1 is w_s2

    def test_AsEncodedObject(self, space, api):
        ptr = space.wrap('abc')

        errors = rffi.str2charp("strict")

        encoding = rffi.str2charp("hex")
        res = api.PyString_AsEncodedObject(
            ptr, encoding, errors)
        assert space.unwrap(res) == "616263"

        res = api.PyString_AsEncodedObject(
            ptr, encoding, lltype.nullptr(rffi.CCHARP.TO))
        assert space.unwrap(res) == "616263"
        rffi.free_charp(encoding)

        encoding = rffi.str2charp("unknown_encoding")
        self.raises(space, api, LookupError, api.PyString_AsEncodedObject,
                    ptr, encoding, errors)
        rffi.free_charp(encoding)

        rffi.free_charp(errors)

        res = api.PyString_AsEncodedObject(
            ptr, lltype.nullptr(rffi.CCHARP.TO), lltype.nullptr(rffi.CCHARP.TO))
        assert space.unwrap(res) == "abc"

        self.raises(space, api, TypeError, api.PyString_AsEncodedObject,
            space.wrap(2), lltype.nullptr(rffi.CCHARP.TO), lltype.nullptr(rffi.CCHARP.TO)
        )

    def test_AsDecodedObject(self, space, api):
        w_str = space.wrap('caf\xe9')
        encoding = rffi.str2charp("latin-1")
        w_res = api.PyString_AsDecodedObject(w_str, encoding, None)
        rffi.free_charp(encoding)
        assert space.unwrap(w_res) == u"caf\xe9"

    def test_eq(self, space, api):
        assert 1 == api._PyString_Eq(space.wrap("hello"), space.wrap("hello"))
        assert 0 == api._PyString_Eq(space.wrap("hello"), space.wrap("world"))

    def test_join(self, space, api):
        w_sep = space.wrap('<sep>')
        w_seq = space.wrap(['a', 'b'])
        w_joined = api._PyString_Join(w_sep, w_seq)
        assert space.unwrap(w_joined) == 'a<sep>b'

