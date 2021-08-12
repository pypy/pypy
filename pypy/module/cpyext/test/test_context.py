import pytest
import sys
import StringIO

from pypy.module.cpyext.state import State
from pypy.module.cpyext.pyobject import make_ref
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from rpython.rtyper.lltypesystem import rffi

class AppTestContext(AppTestCpythonExtensionBase):

    def test_context(self):
        module = self.import_extension('foo', [
            ("new", "METH_VARARGS",
             '''
                PyObject *obj = NULL;
                const char *name;
                if (!PyArg_ParseTuple(args, "s|O:new", &name, &obj)) {
                    return NULL;
                }
                return PyContextVar_New(name, obj);
             '''
             ),
            ("set", "METH_VARARGS",
             '''
                PyObject *obj, *val;
                const char *name;
                if (!PyArg_ParseTuple(args, "OO:set", &obj, &val)) {
                    return NULL;
                }
                return PyContextVar_Set(obj, val);
             '''
             ),
            ("get", "METH_VARARGS",
             '''
                PyObject *obj, *def=NULL, *val;
                const char *name;
                if (!PyArg_ParseTuple(args, "O|O:get", &obj, &def)) {
                    return NULL;
                }
                if (PyContextVar_Get(obj, def, &val) < 0) {
                    return NULL;
                }
                if (val == NULL) {
                    Py_RETURN_NONE;
                }
                return val;

             '''
             ),
            ])
        var = module.new("testme", 3)
        tok = module.set(var, 4)
        assert tok.var is var
        four = module.get(var)
        assert four == 4

        # no default
        var = module.new("testme")
        five = module.get(var, 5)
        assert five == 5


