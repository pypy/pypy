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
        static PyObject* foo_test_FromLong(PyObject* self, PyObject *args)
        {
            int i;
            for(i=-3; i<3; i++)
            {
                PyObject* obj = PyBool_FromLong(i);
                PyObject* expected = (i ? Py_True : Py_False);
                
                if(obj != expected)
                {
                    Py_DECREF(obj);
                    Py_RETURN_FALSE;
                }
                Py_DECREF(obj);
            }
            Py_RETURN_TRUE;
        }
        static PyMethodDef methods[] = {
            { "get_true", foo_get_true, METH_NOARGS },
            { "get_false", foo_get_false, METH_NOARGS },
            { "test_FromLong", foo_test_FromLong, METH_NOARGS },
            { NULL }
        };
        """
        module = self.import_module(name='foo', init=init, body=body)
        assert 'foo' in sys.modules
        assert module.get_true() == True
        assert module.get_false() == False
        assert module.test_FromLong() == True
