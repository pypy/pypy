# encoding: utf-8
import pytest
from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.interpreter.error import OperationError
from pypy.module.cpyext.test.test_api import BaseApiTest, raises_w
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.bytesobject import new_empty_str, PyBytesObject
from pypy.module.cpyext.api import PyObjectP, PyObject, Py_ssize_tP, generic_cpy_call, Py_buffer
from pypy.module.cpyext.pyobject import Py_DecRef, from_ref, make_ref, as_pyobj
from pypy.module.cpyext.api import PyTypeObjectPtr


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
        assert module.test_Size()
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
                PyObject *obj;
                base = PyBytes_FromString("test");
                if (PyBytes_GET_SIZE(base) != 4)
                    return PyLong_FromLong(-PyBytes_GET_SIZE(base));
                type = base->ob_type;
                if (type->tp_itemsize != 1)
                    return PyLong_FromLong(type->tp_itemsize);
                obj = type->tp_alloc(type, 10);
                if (PyBytes_GET_SIZE(obj) != 10)
                    return PyLong_FromLong(PyBytes_GET_SIZE(obj));
                /* cannot work, there is only RO access
                memcpy(PyBytes_AS_STRING(obj), "works", 6); */
                Py_INCREF(obj);
                return obj;
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

    def test_FromFormat(self):
        module = self.import_extension('foo', [
            ("fmt", "METH_VARARGS",
             """
                PyObject* fmt = PyTuple_GetItem(args, 0);
                int n = PyLong_AsLong(PyTuple_GetItem(args, 1));
                PyObject* result = PyBytes_FromFormat(PyBytes_AsString(fmt), n);
                return result;
             """),
        ])
        print(module.fmt(b'd:%d', 10))
        assert module.fmt(b'd:%d', 10) == b'd:10'


class TestBytes(BaseApiTest):
    def test_bytes_resize(self, space, api):
        py_str = new_empty_str(space, 10)
        ar = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        py_str.c_ob_sval[0] = 'a'
        py_str.c_ob_sval[1] = 'b'
        py_str.c_ob_sval[2] = 'c'
        ar[0] = rffi.cast(PyObject, py_str)
        api._PyBytes_Resize(ar, 3)
        py_str = rffi.cast(PyBytesObject, ar[0])
        assert py_str.c_ob_size == 3
        assert py_str.c_ob_sval[1] == 'b'
        assert py_str.c_ob_sval[3] == '\x00'
        # the same for growing
        ar[0] = rffi.cast(PyObject, py_str)
        api._PyBytes_Resize(ar, 10)
        py_str = rffi.cast(PyBytesObject, ar[0])
        assert py_str.c_ob_size == 10
        assert py_str.c_ob_sval[1] == 'b'
        assert py_str.c_ob_sval[10] == '\x00'
        Py_DecRef(space, ar[0])
        lltype.free(ar, flavor='raw')

    def test_Concat(self, space, api):
        ref = make_ref(space, space.newbytes('abc'))
        ptr = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        ptr[0] = ref
        prev_refcnt = ref.c_ob_refcnt
        api.PyBytes_Concat(ptr, space.newbytes('def'))
        assert ref.c_ob_refcnt == prev_refcnt - 1
        assert space.bytes_w(from_ref(space, ptr[0])) == 'abcdef'
        api.PyBytes_Concat(ptr, space.w_None)
        assert not ptr[0]
        api.PyErr_Clear()
        ptr[0] = lltype.nullptr(PyObject.TO)
        api.PyBytes_Concat(ptr, space.newbytes('def')) # should not crash
        lltype.free(ptr, flavor='raw')

    def test_ConcatAndDel(self, space, api):
        ref1 = make_ref(space, space.newbytes('abc'))
        ref2 = make_ref(space, space.newbytes('def'))
        ptr = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        ptr[0] = ref1
        prev_refcnf = ref2.c_ob_refcnt
        api.PyBytes_ConcatAndDel(ptr, ref2)
        assert space.bytes_w(from_ref(space, ptr[0])) == 'abcdef'
        assert ref2.c_ob_refcnt == prev_refcnf - 1
        Py_DecRef(space, ptr[0])
        ptr[0] = lltype.nullptr(PyObject.TO)
        ref2 = make_ref(space, space.newbytes('foo'))
        prev_refcnf = ref2.c_ob_refcnt
        api.PyBytes_ConcatAndDel(ptr, ref2) # should not crash
        assert ref2.c_ob_refcnt == prev_refcnf - 1
        lltype.free(ptr, flavor='raw')

    def test_asbuffer(self, space, api):
        bufp = lltype.malloc(rffi.CCHARPP.TO, 1, flavor='raw')
        lenp = lltype.malloc(Py_ssize_tP.TO, 1, flavor='raw')

        w_text = space.newbytes("text")
        ref = make_ref(space, w_text)
        prev_refcnt = ref.c_ob_refcnt
        assert api.PyObject_AsCharBuffer(ref, bufp, lenp) == 0
        assert ref.c_ob_refcnt == prev_refcnt
        assert lenp[0] == 4
        assert rffi.charp2str(bufp[0]) == 'text'
        lltype.free(bufp, flavor='raw')
        lltype.free(lenp, flavor='raw')
        api.Py_DecRef(ref)

    def test_eq(self, space, api):
        assert 1 == api._PyBytes_Eq(space.newbytes("hello"), space.newbytes("hello"))
        assert 0 == api._PyBytes_Eq(space.newbytes("hello"), space.newbytes("world"))

    def test_join(self, space, api):
        w_sep = space.newbytes('<sep>')
        w_seq = space.newtuple([space.newbytes('a'), space.newbytes('b')])
        w_joined = api._PyBytes_Join(w_sep, w_seq)
        assert space.bytes_w(w_joined) == 'a<sep>b'

    def test_FromObject(self, space, api):
        w_obj = space.newbytes("test")
        assert space.eq_w(w_obj, api.PyBytes_FromObject(w_obj))
        w_obj = space.call_function(space.w_bytearray, w_obj)
        assert space.eq_w(w_obj, api.PyBytes_FromObject(w_obj))
        w_obj = space.wrap(u"test")
        assert api.PyBytes_FromObject(w_obj) is None
        api.PyErr_Clear()

    def test_suboffsets(self, space, api):
        w_bytes = space.newbytes('1234')
        view = lltype.malloc(Py_buffer, flavor='raw', zero=True)
        flags = rffi.cast(rffi.INT_real, 0)
        api.PyObject_GetBuffer(w_bytes, view, flags)
        assert not view.c_suboffsets
