from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

import py
import sys

class AppTestStringObject(AppTestCpythonExtensionBase):
    def test_stringobject(self):
        import sys
        init = """
        if (Py_IsInitialized())
            Py_InitModule("foo", methods);
        """
        body = """
        static PyObject* foo_get_hello1(PyObject* self, PyObject *args)
        {
            return PyString_FromStringAndSize("Hello world<should not be included>", 11);
        }
        static PyObject* foo_get_hello2(PyObject* self, PyObject *args)
        {
            return PyString_FromString("Hello world");
        }
        static PyMethodDef methods[] = {
            { "get_hello1", foo_get_hello1, METH_NOARGS },
            { "get_hello2", foo_get_hello2, METH_NOARGS },
            { NULL }
        };
        """
        module = self.import_module(name='foo', init=init, body=body)
        assert 'foo' in sys.modules
        assert module.get_hello1() == 'Hello world'
        assert module.get_hello2() == 'Hello world'
