from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

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

                 if(PyString_Size(s) == 11) {
                     result = 1;
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
            ])
        assert module.get_hello1() == 'Hello world'
        assert module.get_hello2() == 'Hello world'
        assert module.test_Size()
        raises(TypeError, "module.test_Size_exception()")
