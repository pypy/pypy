from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

import py
import sys

class AppTestBoolObject(AppTestCpythonExtensionBase):
    def test_boolobject(self):
        module = self.import_extension('foo', [
            ("get_true", "METH_NOARGS",  "Py_RETURN_TRUE;"),
            ("get_false", "METH_NOARGS", "Py_RETURN_FALSE;"),
            ("test_FromLong", "METH_NOARGS",
             """
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
             """),
            ("test_Check", "METH_NOARGS",
             """
                 int result = 0;
                 PyObject* f = PyFloat_FromDouble(1.0);

                 if(PyBool_Check(Py_True) &&
                    PyBool_Check(Py_False) &&
                    !PyBool_Check(f))
                 {
                     result = 1;
                 }
                 Py_DECREF(f);
                 return PyBool_FromLong(result);
             """),
            ])
        assert module.get_true() == True
        assert module.get_false() == False
        assert module.test_FromLong() == True
        assert module.test_Check() == True
        self.check_refcnts("FOOOOOO %r")
