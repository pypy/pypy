from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.test.test_api import BaseApiTest

class TestBoolObject(BaseApiTest):
    def test_fromlong(self, space, api):
        for i in range(-3, 3):
            obj = api.PyBool_FromLong(i)
            if i:
                assert obj is space.w_True
            else:
                assert obj is space.w_False

    def test_check(self, space, api):
        assert api.PyBool_Check(space.w_True)
        assert api.PyBool_Check(space.w_False)
        assert not api.PyBool_Check(space.w_None)
        assert not api.PyBool_Check(api.PyFloat_FromDouble(1.0))

class AppTestBoolMacros(AppTestCpythonExtensionBase):
    def test_macros(self):
        module = self.import_extension('foo', [
            ("get_true", "METH_NOARGS",  "Py_RETURN_TRUE;"),
            ("get_false", "METH_NOARGS", "Py_RETURN_FALSE;"),
            ])
        assert module.get_true() == True
        assert module.get_false() == False
