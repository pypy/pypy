
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

class AppTestGetargs(AppTestCpythonExtensionBase):
    def test_pyarg_parse(self):
        mod = self.import_extension('foo', [
            ('oneargint', 'METH_VARARGS',
             '''
             int l;
             if (!PyArg_ParseTuple(args, "i", &l)) {
                 return NULL;
             }
             return PyInt_FromLong(l);
             '''
             ),
            ('oneargandform', 'METH_VARARGS',
             '''
             int l;
             if (!PyArg_ParseTuple(args, "i:oneargandstuff", &l)) {
                 return NULL;
             }
             return PyInt_FromLong(l);
             '''),
            ('oneargobject', 'METH_VARARGS',
             '''
             PyObject *obj;
             if (!PyArg_ParseTuple(args, "O", &obj)) {
                 return NULL;
             }
             Py_INCREF(obj);
             return obj;
             '''),
            ('oneargobjectandlisttype', 'METH_VARARGS',
             '''
             PyObject *obj;
             if (!PyArg_ParseTuple(args, "O!", &PyList_Type, &obj)) {
                 return NULL;
             }
             Py_INCREF(obj);
             return obj;
             '''),
            ('twoopt', 'METH_VARARGS',
             '''
             PyObject *a;
             PyObject *b = NULL;
             if (!PyArg_ParseTuple(args, "O|O", &a, &b)) {
                 return NULL;
             }
             if (b)
                 Py_INCREF(b);
             else
                 b = PyInt_FromLong(42);
             /* return an owned reference */
             return b;
             ''')])
        assert mod.oneargint(1) == 1
        raises(TypeError, mod.oneargint, None)
        raises(TypeError, mod.oneargint)
        assert mod.oneargandform(1) == 1

        sentinel = object()
        res = mod.oneargobject(sentinel)
        raises(TypeError, "mod.oneargobjectandlisttype(sentinel)")
        assert res is sentinel
        assert mod.twoopt(1) == 42
        assert mod.twoopt(1, 2) == 2
        raises(TypeError, mod.twoopt, 1, 2, 3)
