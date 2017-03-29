import pytest
from pypy.interpreter.error import OperationError
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from rpython.rtyper.lltypesystem import rffi
from pypy.module.cpyext.floatobject import (
    PyFloat_FromDouble, PyFloat_AsDouble, PyFloat_AS_DOUBLE, PyNumber_Float,
    _PyFloat_Unpack4, _PyFloat_Unpack8)

class TestFloatObject(BaseApiTest):
    def test_floatobject(self, space):
        assert space.unwrap(PyFloat_FromDouble(space, 3.14)) == 3.14
        assert PyFloat_AsDouble(space, space.wrap(23.45)) == 23.45
        assert PyFloat_AS_DOUBLE(space, space.wrap(23.45)) == 23.45
        with pytest.raises(OperationError):
            PyFloat_AsDouble(space, space.w_None)

    def test_coerce(self, space):
        assert space.type(PyNumber_Float(space, space.wrap(3))) is space.w_float
        assert space.type(PyNumber_Float(space, space.wrap("3"))) is space.w_float

        w_obj = space.appexec([], """():
            class Coerce(object):
                def __float__(self):
                    return 42.5
            return Coerce()""")
        assert space.eq_w(PyNumber_Float(space, w_obj), space.wrap(42.5))

    def test_unpack(self, space):
        with rffi.scoped_str2charp("\x9a\x99\x99?") as ptr:
            assert abs(_PyFloat_Unpack4(space, ptr, 1) - 1.2) < 1e-7
        with rffi.scoped_str2charp("?\x99\x99\x9a") as ptr:
            assert abs(_PyFloat_Unpack4(space, ptr, 0) - 1.2) < 1e-7
        with rffi.scoped_str2charp("\x1f\x85\xebQ\xb8\x1e\t@") as ptr:
            assert abs(_PyFloat_Unpack8(space, ptr, 1) - 3.14) < 1e-15
        with rffi.scoped_str2charp("@\t\x1e\xb8Q\xeb\x85\x1f") as ptr:
            assert abs(_PyFloat_Unpack8(space, ptr, 0) - 3.14) < 1e-15

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

class AppTestFloatMacros(AppTestCpythonExtensionBase):
    def test_return_nan(self):
        import math

        module = self.import_extension('foo', [
            ("return_nan", "METH_NOARGS",
             "Py_RETURN_NAN;"),
            ])
        assert math.isnan(module.return_nan())

    def test_return_inf(self):
        import math

        module = self.import_extension('foo', [
            ("return_inf", "METH_NOARGS",
             "Py_RETURN_INF(10);"),
            ])
        inf = module.return_inf()
        assert inf > 0
        assert math.isinf(inf)

    def test_return_inf_negative(self):
        import math

        module = self.import_extension('foo', [
            ("return_neginf", "METH_NOARGS",
             "Py_RETURN_INF(-10);"),
            ])
        neginf = module.return_neginf()
        assert neginf < 0
        assert math.isinf(neginf)

    def test_macro_accepts_wrong_pointer_type(self):
        module = self.import_extension('foo', [
            ("test_macros", "METH_NOARGS",
             """
             PyObject* o = PyFloat_FromDouble(1.0);
             // no PyFloatObject
             char* dumb_pointer = (char*)o;

             PyFloat_AS_DOUBLE(o);
             PyFloat_AS_DOUBLE(dumb_pointer);

             Py_RETURN_NONE;"""),
            ])
