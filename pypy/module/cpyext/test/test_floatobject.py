from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

import py
import sys

class AppTestFloatObject(AppTestCpythonExtensionBase):
    def test_floatobject(self):
        module = self.import_extension('foo', [
            ("FromDouble", "METH_NOARGS",
             """
                 return PyFloat_FromDouble(3.14);
             """),
            ("AsDouble", "METH_NOARGS",
             """
                 PyObject* obj = PyFloat_FromDouble(23.45);
                 double d = PyFloat_AsDouble(obj);
                 Py_DECREF(obj);
                 return PyFloat_FromDouble(d);
             """),
            ])
        assert module.FromDouble() == 3.14
        assert module.AsDouble() == 23.45
