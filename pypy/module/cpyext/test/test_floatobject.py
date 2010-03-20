from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

import py
import sys

class AppTestFloatObject(AppTestCpythonExtensionBase):
    def test_floatobject(self):
        import sys
        init = """
        if (Py_IsInitialized())
            Py_InitModule("foo", methods);
        """
        body = """
        PyObject* foo_FromDouble(PyObject* self, PyObject *args)
        {
            return PyFloat_FromDouble(3.14);
        }
        double foo_AsDouble(PyObject* self, PyObject *args)
        {
            PyObject* pi = PyFloat_FromDouble(3.14);
            return PyFloat_AsDouble(pi);
        }
        static PyMethodDef methods[] = {
            { "FromDouble", foo_FromDouble, METH_NOARGS },
            { "AsDouble", foo_AsDouble, METH_NOARGS },
            { NULL }
        };
        """
        module = self.import_module(name='foo', init=init, body=body)
        assert 'foo' in sys.modules
        assert module.FromDouble() == 3.14
        assert module.AsDouble() == 3.14
