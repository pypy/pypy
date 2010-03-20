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
        static PyObject* foo_get_true(PyObject* self, PyObject *args)
        {
            Py_RETURN_TRUE;
        }
        static PyObject* foo_get_false(PyObject* self, PyObject *args)
        {
            Py_RETURN_FALSE;
        }
        static PyMethodDef methods[] = {
            { "get_true", foo_get_true, METH_NOARGS },
            { "get_false", foo_get_false, METH_NOARGS },
            { NULL }
        };
        """
        module = self.import_module(name='foo', init=init, body=body)
        assert 'foo' in sys.modules
        assert module.get_true() == True
        assert module.get_false() == False
