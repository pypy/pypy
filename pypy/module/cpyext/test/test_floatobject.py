from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from rpython.rtyper.lltypesystem import rffi

class TestFloatObject(BaseApiTest):
    def test_floatobject(self, space, api):
        assert space.unwrap(api.PyFloat_FromDouble(3.14)) == 3.14
        assert api.PyFloat_AsDouble(space.wrap(23.45)) == 23.45
        assert api.PyFloat_AS_DOUBLE(space.wrap(23.45)) == 23.45

        assert api.PyFloat_AsDouble(space.w_None) == -1
        api.PyErr_Clear()

    def test_coerce(self, space, api):
        assert space.type(api.PyNumber_Float(space.wrap(3))) is space.w_float
        assert space.type(api.PyNumber_Float(space.wrap("3"))) is space.w_float

        w_obj = space.appexec([], """():
            class Coerce(object):
                def __float__(self):
                    return 42.5
            return Coerce()""")
        assert space.eq_w(api.PyNumber_Float(w_obj), space.wrap(42.5))

    def test_unpack(self, space, api):
        with rffi.scoped_str2charp("\x9a\x99\x99?") as ptr:
            assert abs(api._PyFloat_Unpack4(ptr, 1) - 1.2) < 1e-7
        with rffi.scoped_str2charp("?\x99\x99\x9a") as ptr:
            assert abs(api._PyFloat_Unpack4(ptr, 0) - 1.2) < 1e-7
        with rffi.scoped_str2charp("\x1f\x85\xebQ\xb8\x1e\t@") as ptr:
            assert abs(api._PyFloat_Unpack8(ptr, 1) - 3.14) < 1e-15
        with rffi.scoped_str2charp("@\t\x1e\xb8Q\xeb\x85\x1f") as ptr:
            assert abs(api._PyFloat_Unpack8(ptr, 0) - 3.14) < 1e-15

class AppTestFloatObject(AppTestCpythonExtensionBase):
    def test_fromstring(self):
        module = self.import_extension('foo', [
            ("from_string", "METH_NOARGS",
             """
                 PyObject* str = PyString_FromString("1234.56");
                 PyObject* res = PyFloat_FromString(str, NULL);
                 Py_DECREF(str);
                 return res;
             """),
            ])
        assert module.from_string() == 1234.56
        assert type(module.from_string()) is float
