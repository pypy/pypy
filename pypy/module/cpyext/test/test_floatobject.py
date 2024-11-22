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
                 PyObject* str = PyUnicode_FromString("1234.56");
                 PyObject* res = PyFloat_FromString(str);
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

    def test_PyFloat_Check(self):
        module = self.import_extension('foo', [
            ("test", "METH_NOARGS",
             """
             PyObject* pyobj = PyFloat_FromDouble(1.0);
             PyFloatObject* pfo = (PyFloatObject*)pyobj;
             int res = (PyFloat_Check(pyobj) +
                        PyFloat_CheckExact(pyobj) * 10 +
                        PyFloat_Check(pfo) * 100 +
                        PyFloat_CheckExact(pfo) * 1000);
             Py_DecRef(pyobj);
             return PyLong_FromLong(res);"""),
            ])
        assert module.test() == 1111

    def test_pymath_consts(self):
        # test preprocessor constants in their string form to avoid
        # floating-point conversion issues (and to avoid having to
        # conditionalize on compiler support for long double)
        for const_name, const_strval in [
                ('Py_MATH_PIl', b"3.1415926535897932384626433832795029L"),
                ('Py_MATH_PI', b"3.14159265358979323846"),
                ('Py_MATH_El', b"2.7182818284590452353602874713526625L"),
                ('Py_MATH_E', b"2.7182818284590452354"),
                ('Py_MATH_TAU', b"6.2831853071795864769252867665590057683943L"),
            ]:
            module = self.import_extension('foo_%s' % const_name, [
                ("test", "METH_NOARGS",
                 """
                 #define xstr(s) str(s)
                 #define str(s) #s
                 return PyBytes_FromString(xstr(%s));""" % const_name)
            ])
            assert module.test() == const_strval

    def test_Py_IS_NAN(self):
        module = self.import_extension('foo', [
            ("test", "METH_O",
             """
                 double d = PyFloat_AsDouble(args);
                 return PyBool_FromLong(Py_IS_NAN(d));
             """),
            ])
        assert not module.test(0)
        assert not module.test(1)
        assert not module.test(-1)
        assert not module.test(float('inf'))
        assert module.test(float('nan'))

    def test_Py_IS_INFINITY(self):
        module = self.import_extension('foo', [
            ("test", "METH_O",
             """
                 double d = PyFloat_AsDouble(args);
                 return PyBool_FromLong(Py_IS_INFINITY(d));
             """),
            ])
        assert not module.test(0)
        assert not module.test(1)
        assert not module.test(-1)
        assert not module.test(float('nan'))
        assert module.test(float('inf'))
        assert module.test(float('-inf'))

    def test_Py_IS_FINITE(self):
        module = self.import_extension('foo', [
            ("test", "METH_O",
             """
                 double d = PyFloat_AsDouble(args);
                 return PyBool_FromLong(Py_IS_FINITE(d));
             """),
            ])
        assert module.test(0)
        assert module.test(1)
        assert module.test(-1)
        assert not module.test(float('nan'))
        assert not module.test(float('inf'))
        assert not module.test(float('-inf'))

    def test_Py_Float_AsDouble_err(self):
        module = self.import_extension('foo', [
            ("test", "METH_O",
             """
                double d = PyFloat_AsDouble(args);
                if (PyErr_Occurred()) {
                    return NULL;
                }
                return PyFloat_FromDouble(d);
             """),
            ])
        try:
            module.test([])
        except Exception as e:
            print(str(e))
            assert str(e) == 'must be real number, not list'
        else:
            assert False

    def test_Py_HUGE_VAL(self):
        module = self.import_extension('foo', [
            ("test", "METH_NOARGS",
             """
                 return PyFloat_FromDouble(Py_HUGE_VAL);
             """),
            ])
        assert module.test() == float('inf')

    def test_Py_NAN(self):
        import sys
        module = self.import_extension('foo', [
            ("test", "METH_NOARGS",
             """
                 return PyFloat_FromDouble(Py_NAN);
             """),
            ])
        if sys.platform == 'win32':
            # CPython does not enforce bit-compatibility between the NANs
            import math
            assert math.isnan(module.test())
        else:
            import struct
            float_bits = struct.Struct('d').pack
            assert float_bits(module.test()) == float_bits(float('nan'))

    def test_roundtrip(self):
        module = self.import_extension('foo', [
            ("float_pack", "METH_VARARGS",
             """
                int size;
                double d;
                int le;
                if (!PyArg_ParseTuple(args, "idi", &size, &d, &le)) {
                    return NULL;
                }
                switch (size)
                {
                case 2:
                {
                    char data[2];
                    if (PyFloat_Pack2(d, data, le) < 0) {
                        return NULL;
                    }
                    return PyBytes_FromStringAndSize(data, Py_ARRAY_LENGTH(data));
                }
                case 4:
                {
                    char data[4];
                    if (PyFloat_Pack4(d, data, le) < 0) {
                        return NULL;
                    }
                    return PyBytes_FromStringAndSize(data, Py_ARRAY_LENGTH(data));
                }
                case 8:
                {
                    char data[8];
                    if (PyFloat_Pack8(d, data, le) < 0) {
                        return NULL;
                    }
                    return PyBytes_FromStringAndSize(data, Py_ARRAY_LENGTH(data));
                }
                default: break;
                }

                PyErr_SetString(PyExc_ValueError, "size must 2, 4 or 8");
                return NULL;
             """),
            ("float_unpack", "METH_VARARGS",
             """
                assert(!PyErr_Occurred());
                const char *data;
                Py_ssize_t size;
                int le;
                if (!PyArg_ParseTuple(args, "y#i", &data, &size, &le)) {
                    return NULL;
                }
                double d;
                switch (size)
                {
                case 2:
                    d = PyFloat_Unpack2(data, le);
                    break;
                case 4:
                    d = PyFloat_Unpack4(data, le);
                    break;
                case 8:
                    d = PyFloat_Unpack8(data, le);
                    break;
                default:
                    PyErr_SetString(PyExc_ValueError, "data length must 2, 4 or 8 bytes");
                    return NULL;
                }

                if (d == -1.0 && PyErr_Occurred()) {
                    return NULL;
                }
                return PyFloat_FromDouble(d);
             """),
        ], PY_SSIZE_T_CLEAN=1)
        import math
        HAVE_IEEE_754 = float.__getformat__("double").startswith("IEEE")
        INF = float("inf")
        NAN = float("nan")
        BIG_ENDIAN = 0
        LITTLE_ENDIAN = 1
        EPSILON = {
            2: 2.0 ** -11,  # binary16
            4: 2.0 ** -24,  # binary32
            8: 2.0 ** -53,  # binary64
}
        large = 2.0 ** 100
        values = [1.0, 1.5, large, 1.0/7, math.pi]
        if HAVE_IEEE_754:
            values.extend((INF, NAN))
        for value in values:
            for size in (2, 4, 8,):
                if size == 2 and value == large:
                    # too large for 16-bit float
                    continue
                rel_tol = EPSILON[size]
                for endian in (BIG_ENDIAN, LITTLE_ENDIAN):
                    data = module.float_pack(size, value, endian)
                    value2 = module.float_unpack(data, endian)
                    if math.isnan(value):
                        assert math.isnan(value2), (value, value2)
                    elif size < 8:
                        assert math.isclose(value2, value, rel_tol=rel_tol), (value, value2)
                    else:
                        assert value2 == value


