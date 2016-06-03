from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

class AppTestStringObject(AppTestCpythonExtensionBase):
    def test_basic(self):
        module = self.import_extension('foo', [
            ("get_hello1", "METH_NOARGS",
             """
                 return PyByteArray_FromStringAndSize(
                     "Hello world<should not be included>", 11);
             """),
            ("get_hello2", "METH_NOARGS",
             """
                 return PyByteArray_FromStringAndSize("Hello world", 12);
             """),
            ("test_Size", "METH_NOARGS",
             """
                 PyObject* s = PyByteArray_FromStringAndSize("Hello world", 12);
                 int result = 0;
                 size_t expected_size;

                 if(PyByteArray_Size(s) == 12) {
                     result = 1;
                 }
                 #ifdef PYPY_VERSION
                    expected_size = sizeof(void*)*3;
                 #elif defined Py_DEBUG
                    expected_size = 64;
                 #else
                    expected_size = 48;
                 #endif
                 if(s->ob_type->tp_basicsize != expected_size)
                 {
                     printf("tp_basicsize==%ld\\n", s->ob_type->tp_basicsize); 
                     result = 0;
                 }
                 Py_DECREF(s);
                 return PyBool_FromLong(result);
             """),
             ("test_is_bytearray", "METH_VARARGS",
             """
                return PyBool_FromLong(PyByteArray_Check(PyTuple_GetItem(args, 0)));
             """)], prologue='#include <stdlib.h>')
        assert module.get_hello1() == 'Hello world'
        assert module.get_hello2() == 'Hello world\x00'
        assert module.test_Size()
        assert module.test_is_bytearray(bytearray(""))
        assert not module.test_is_bytearray(())

    def test_bytearray_buffer_init(self):
        module = self.import_extension('foo', [
            ("getbytearray", "METH_NOARGS",
             """
                 PyObject *s, *t;
                 char* c;
                 Py_ssize_t len;

                 s = PyByteArray_FromStringAndSize(NULL, 4);
                 if (s == NULL)
                    return NULL;
                 t = PyByteArray_FromStringAndSize(NULL, 3);
                 if (t == NULL)
                    return NULL;
                 Py_DECREF(t);
                 c = PyByteArray_AsString(s);
                 if (c == NULL)
                 {
                     PyErr_SetString(PyExc_ValueError, "non-null bytearray object expected");
                     return NULL;
                 }
                 c[0] = 'a';
                 c[1] = 'b';
                 c[2] = 0;
                 c[3] = 'c';
                 return s;
             """),
            ])
        s = module.getbytearray()
        assert len(s) == 4
        assert s == 'ab\x00c'

    def test_bytearray_mutable(self):
        module = self.import_extension('foo', [
            ("mutable", "METH_NOARGS",
             """
                PyObject *base;
                char * p_str;
                base = PyByteArray_FromStringAndSize("test", 10);
                if (PyByteArray_GET_SIZE(base) != 10)
                    return PyLong_FromLong(-PyByteArray_GET_SIZE(base));
                memcpy(PyByteArray_AS_STRING(base), "works", 6); 
                Py_INCREF(base);
                return base;
             """),
            ])
        s = module.mutable()
        if s == '\x00' * 10:
            assert False, "no RW access to bytearray"
        assert s[:6] == 'works\x00'

    def test_AsByteArray(self):
        module = self.import_extension('foo', [
            ("getbytearray", "METH_NOARGS",
             """
                 PyObject* s1 = PyByteArray_FromStringAndSize("test", 4);
                 if (s1 == NULL)
                     return NULL;
                 char* c = PyByteArray_AsString(s1);
                 PyObject* s2 = PyByteArray_FromStringAndSize(c, 4);
                 Py_DECREF(s1);
                 return s2;
             """),
            ])
        s = module.getbytearray()
        assert s == 'test'

    def test_manipulations(self):
        module = self.import_extension('foo', [
            ("bytearray_from_string", "METH_VARARGS",
             '''
             return PyByteArray_FromStringAndSize(PyString_AsString(
                       PyTuple_GetItem(args, 0)), 4);
             '''
            ),
            ("str_from_bytearray", "METH_VARARGS",
             '''
                char * buf;
                int n;
                PyObject * obj;
                obj = PyTuple_GetItem(args, 0);
                buf = PyByteArray_AsString(obj);
                if (buf == NULL)
                {
                    PyErr_SetString(PyExc_ValueError, "non-null bytearray object expected");
                    return NULL;
                }
                n = PyByteArray_Size(obj);
                return PyString_FromStringAndSize(buf, n);
             '''
            ),
            ("concat", "METH_VARARGS",
             """
                PyObject * ret, *right, *left;
                PyObject *ba1, *ba2; 
                if (!PyArg_ParseTuple(args, "OO", &left, &right)) {
                    return PyString_FromString("parse failed"); 
                }
                ba1 = PyByteArray_FromObject(left);
                ba2 = PyByteArray_FromObject(right);
                if (ba1 == NULL || ba2 == NULL)
                {
                    /* exception should be set */
                    return NULL;
                }
                ret = PyByteArray_Concat(ba1, ba2);
                return ret;
             """)])
        assert module.bytearray_from_string("huheduwe") == "huhe"
        assert module.str_from_bytearray(bytearray('abc')) == 'abc'
        raises(ValueError, module.str_from_bytearray, 4.0)
        ret = module.concat('abc', 'def')
        assert ret == 'abcdef'
        assert not isinstance(ret, str)
        assert isinstance(ret, bytearray)
        raises(TypeError, module.concat, 'abc', u'def')

    def test_bytearray_resize(self):
        module = self.import_extension('foo', [
            ("bytearray_resize", "METH_VARARGS",
             '''
             PyObject *obj, *ba;
             int newsize, oldsize, ret;
             if (!PyArg_ParseTuple(args, "Oi", &obj, &newsize)) {
                 return PyString_FromString("parse failed"); 
             }
             
             ba = PyByteArray_FromObject(obj);
             if (ba == NULL)
                 return NULL;
             oldsize = PyByteArray_Size(ba);
             if (oldsize == 0)
             {
                  return PyString_FromString("oldsize is 0");
             }
             ret = PyByteArray_Resize(ba, newsize);
             if (ret != 0)
             {
                  printf("ret, oldsize, newsize= %d, %d, %d\\n", ret, oldsize, newsize);
                  return NULL;
             } 
             return ba;
             '''
            )])
        ret = module.bytearray_resize('abc', 6)
        assert len(ret) == 6,"%s, len=%d" % (ret, len(ret))
        assert ret == 'abc\x00\x00\x00'
        ret = module.bytearray_resize('abcdefghi', 4)
        assert len(ret) == 4,"%s, len=%d" % (ret, len(ret))
        assert ret == 'abcd'

