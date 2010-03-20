from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

import py
import sys

class AppTestBoolObject(AppTestCpythonExtensionBase):
    def test_boolobject(self):
        import sys
        init = """
        if (Py_IsInitialized())
            Py_InitModule("foo", methods);
        """
        body = """
        static PyObject* foo_GetTrue(PyObject* self, PyObject *args)
        {
            Py_INCREF(Py_True);
            return Py_True;
        }
        static PyObject* foo_GetFalse(PyObject* self, PyObject *args)
        {
            Py_INCREF(Py_False);
            return Py_False;
        }
        static PyMethodDef methods[] = {
            { "GetTrue", foo_GetTrue, METH_NOARGS },
            { "GetFalse", foo_GetFalse, METH_NOARGS },
            { NULL }
        };
        """
        module = self.import_module(name='foo', init=init, body=body)
        assert 'foo' in sys.modules
        assert module.GetTrue() == True
        assert module.GetFalse() == False
