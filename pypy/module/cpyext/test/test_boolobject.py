from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.boolobject import PyBool_Check, PyBool_FromLong
from pypy.module.cpyext.floatobject import PyFloat_FromDouble

class TestBoolObject(BaseApiTest):
    def test_fromlong(self, space):
        for i in range(-3, 3):
            obj = PyBool_FromLong(space, i)
            if i:
                assert obj is space.w_True
            else:
                assert obj is space.w_False

    def test_check(self, space):
        assert PyBool_Check(space, space.w_True)
        assert PyBool_Check(space, space.w_False)
        assert not PyBool_Check(space, space.w_None)
        assert not PyBool_Check(space, PyFloat_FromDouble(space, 1.0))

class AppTestBoolMacros(AppTestCpythonExtensionBase):
    def test_macros(self):
        module = self.import_extension('foo', [
            ("get_true", "METH_NOARGS",  "Py_RETURN_TRUE;"),
            ("get_false", "METH_NOARGS", "Py_RETURN_FALSE;"),
            ])
        assert module.get_true() == True
        assert module.get_false() == False

    def test_toint(self):
        module = self.import_extension('foo', [
            ("to_int", "METH_O",
            '''
                if (args->ob_type->tp_as_number && args->ob_type->tp_as_number->nb_int) {
                    return args->ob_type->tp_as_number->nb_int(args);
                }
                else {
                    PyErr_SetString(PyExc_TypeError,"cannot convert bool to int");
                    return NULL;
                }
            '''), ])
        assert module.to_int(False) == 0
        assert module.to_int(True) == 1

            
