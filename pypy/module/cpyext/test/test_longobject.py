import sys, py
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib.rarithmetic import maxint
from pypy.objspace.std.longobject import W_LongObject
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase


class TestLongObject(BaseApiTest):
    def test_FromLong(self, space, api):
        w_value = api.PyLong_FromLong(3)
        assert isinstance(w_value, W_LongObject)
        assert space.unwrap(w_value) == 3

        w_value = api.PyLong_FromLong(sys.maxint)
        assert isinstance(w_value, W_LongObject)
        assert space.unwrap(w_value) == sys.maxint

    def test_aslong(self, space, api):
        w_value = api.PyLong_FromLong((sys.maxint - 1) / 2)
        assert isinstance(w_value, W_LongObject)

        w_value = space.mul(w_value, space.wrap(2))
        assert isinstance(w_value, W_LongObject)
        value = api.PyLong_AsLong(w_value)
        assert value == (sys.maxint - 1)

        w_value = space.mul(w_value, space.wrap(2))

        value = api.PyLong_AsLong(w_value)
        assert value == -1 and api.PyErr_Occurred() is space.w_OverflowError
        api.PyErr_Clear()
        value = api.PyLong_AsUnsignedLong(w_value)
        assert value == (sys.maxint - 1) * 2

        self.raises(space, api, OverflowError, api.PyLong_AsUnsignedLong, space.wrap(-1))

    def test_as_ssize_t(self, space, api):
        w_value = space.newlong(2)
        assert isinstance(w_value, W_LongObject)
        value = api.PyLong_AsSsize_t(w_value)
        assert value == 2
        w_val2 = api.PyLong_FromSsize_t(2)
        assert isinstance(w_val2, W_LongObject)
        assert space.eq_w(w_value, w_val2)

    def test_fromdouble(self, space, api):
        w_value = api.PyLong_FromDouble(-12.74)
        assert space.isinstance_w(w_value, space.w_int)
        assert space.unwrap(w_value) == -12
        assert api.PyLong_AsDouble(w_value) == -12

    def test_type_check(self, space, api):
        w_l = space.wrap(sys.maxint + 1)
        assert api.PyLong_Check(w_l)
        assert api.PyLong_CheckExact(w_l)

        w_i = space.wrap(sys.maxint)
        assert api.PyLong_Check(w_i)
        assert api.PyLong_CheckExact(w_i)

        L = space.appexec([], """():
            class L(int):
                pass
            return L
        """)
        l = space.call_function(L)
        assert api.PyLong_Check(l)
        assert not api.PyLong_CheckExact(l)

    def test_as_longlong(self, space, api):
        assert api.PyLong_AsLongLong(space.wrap(1<<62)) == 1<<62
        assert api.PyLong_AsLongLong(space.wrap(1<<63)) == -1
        api.PyErr_Clear()

        assert api.PyLong_AsUnsignedLongLong(space.wrap(1<<63)) == 1<<63
        assert api.PyLong_AsUnsignedLongLong(space.wrap(1<<64)) == (1<<64) - 1
        assert api.PyErr_Occurred()
        api.PyErr_Clear()

        assert api.PyLong_AsUnsignedLongLongMask(
            space.wrap(1<<64)) == 0

        self.raises(space, api, OverflowError, api.PyLong_AsUnsignedLongLong, space.wrap(-1))

    def test_as_long_and_overflow(self, space, api):
        overflow = lltype.malloc(rffi.CArrayPtr(rffi.INT_real).TO, 1, flavor='raw')
        assert api.PyLong_AsLongAndOverflow(
            space.wrap(sys.maxint), overflow) == sys.maxint
        assert api.PyLong_AsLongAndOverflow(
            space.wrap(-sys.maxint - 2), overflow) == -1
        assert not api.PyErr_Occurred()
        assert overflow[0] == -1
        lltype.free(overflow, flavor='raw')

    def test_as_longlong_and_overflow(self, space, api):
        overflow = lltype.malloc(rffi.CArrayPtr(rffi.INT_real).TO, 1, flavor='raw')
        assert api.PyLong_AsLongLongAndOverflow(
            space.wrap(1<<62), overflow) == 1<<62
        assert api.PyLong_AsLongLongAndOverflow(
            space.wrap(1<<63), overflow) == -1
        assert not api.PyErr_Occurred()
        assert overflow[0] == 1
        assert api.PyLong_AsLongLongAndOverflow(
            space.wrap(-1<<64), overflow) == -1
        assert not api.PyErr_Occurred()
        assert overflow[0] == -1
        lltype.free(overflow, flavor='raw')

    def test_as_voidptr(self, space, api):
        w_l = api.PyLong_FromVoidPtr(lltype.nullptr(rffi.VOIDP.TO))
        assert space.is_w(space.type(w_l), space.w_int)
        assert space.unwrap(w_l) == 0
        assert api.PyLong_AsVoidPtr(w_l) == lltype.nullptr(rffi.VOIDP.TO)

        p = rffi.cast(rffi.VOIDP, maxint)
        w_l = api.PyLong_FromVoidPtr(p)
        assert space.is_w(space.type(w_l), space.w_int)
        assert space.unwrap(w_l) == maxint
        assert api.PyLong_AsVoidPtr(w_l) == p

        p = rffi.cast(rffi.VOIDP, -maxint-1)
        w_l = api.PyLong_FromVoidPtr(p)
        assert space.is_w(space.type(w_l), space.w_int)
        assert space.unwrap(w_l) == maxint+1
        assert api.PyLong_AsVoidPtr(w_l) == p

    def test_sign_and_bits(self, space, api):
        if space.is_true(space.lt(space.sys.get('version_info'),
                                  space.wrap((2, 7)))):
            py.test.skip("unsupported before Python 2.7")

        assert api._PyLong_Sign(space.wraplong(0L)) == 0
        assert api._PyLong_Sign(space.wraplong(2L)) == 1
        assert api._PyLong_Sign(space.wraplong(-2L)) == -1

        assert api._PyLong_NumBits(space.wrap(0)) == 0
        assert api._PyLong_NumBits(space.wrap(1)) == 1
        assert api._PyLong_NumBits(space.wrap(-1)) == 1
        assert api._PyLong_NumBits(space.wrap(2)) == 2
        assert api._PyLong_NumBits(space.wrap(-2)) == 2
        assert api._PyLong_NumBits(space.wrap(3)) == 2
        assert api._PyLong_NumBits(space.wrap(-3)) == 2

    def test_as_ulongmask(self, space, api):
        assert api.PyLong_AsUnsignedLongMask(
            space.wrap(sys.maxsize * 2 + 1)) == sys.maxsize * 2 + 1
        assert api.PyLong_AsUnsignedLongMask(
            space.wrap(sys.maxsize * 2 + 2)) == 0

class AppTestLongObject(AppTestCpythonExtensionBase):
    def test_fromunsignedlong(self):
        module = self.import_extension('foo', [
            ("from_unsignedlong", "METH_NOARGS",
             """
                 PyObject * obj;
                 obj = PyLong_FromUnsignedLong((unsigned long)-1);
                 if (obj->ob_type != &PyLong_Type)
                 {
                    Py_DECREF(obj);
                    PyErr_SetString(PyExc_ValueError,
                            "PyLong_FromLongLong did not return PyLongObject");
                    return NULL;
                 }
                 return obj;
             """)])
        import sys
        assert module.from_unsignedlong() == 2 * sys.maxsize + 1

    def test_fromlonglong(self):
        module = self.import_extension('foo', [
            ("from_longlong", "METH_VARARGS",
             """
                 int val;
                 PyObject * obj;
                 if (!PyArg_ParseTuple(args, "i", &val))
                     return NULL;
                 obj = PyLong_FromLongLong((long long)val);
                 if (obj->ob_type != &PyLong_Type)
                 {
                    Py_DECREF(obj);
                    PyErr_SetString(PyExc_ValueError,
                            "PyLong_FromLongLong did not return PyLongObject");
                    return NULL;
                 }
                 return obj;
             """),
            ("from_unsignedlonglong", "METH_VARARGS",
             """
                 int val;
                 PyObject * obj;
                 if (!PyArg_ParseTuple(args, "i", &val))
                     return NULL;
                 obj = PyLong_FromUnsignedLongLong((long long)val);
                 if (obj->ob_type != &PyLong_Type)
                 {
                    Py_DECREF(obj);
                    PyErr_SetString(PyExc_ValueError,
                            "PyLong_FromLongLong did not return PyLongObject");
                    return NULL;
                 }
                 return obj;
             """)])
        assert module.from_longlong(-1) == -1
        assert module.from_longlong(0) == 0
        assert module.from_unsignedlonglong(0) == 0
        assert module.from_unsignedlonglong(-1) == (1<<64) - 1

    def test_from_size_t(self):
        module = self.import_extension('foo', [
            ("from_unsignedlong", "METH_NOARGS",
             """
                 return PyLong_FromSize_t((size_t)-1);
             """)])
        import sys
        assert module.from_unsignedlong() == 2 * sys.maxsize + 1

    def test_fromstring(self):
        module = self.import_extension('foo', [
            ("from_string", "METH_NOARGS",
             """
                 return PyLong_FromString("0x1234", NULL, 0);
             """),
            ])
        assert module.from_string() == 0x1234

    def test_frombytearray(self):
        module = self.import_extension('foo', [
            ("from_bytearray", "METH_VARARGS",
             """
                 int little_endian, is_signed;
                 if (!PyArg_ParseTuple(args, "ii", &little_endian, &is_signed))
                     return NULL;
                 return _PyLong_FromByteArray((unsigned char*)"\\x9A\\xBC", 2,
                                              little_endian, is_signed);
             """),
            ])
        assert module.from_bytearray(True, False) == 0xBC9A
        assert module.from_bytearray(True, True) == -0x4366
        assert module.from_bytearray(False, False) == 0x9ABC
        assert module.from_bytearray(False, True) == -0x6544

    def test_frombytearray_2(self):
        module = self.import_extension('foo', [
            ("from_bytearray", "METH_VARARGS",
             """
                 int little_endian, is_signed;
                 if (!PyArg_ParseTuple(args, "ii", &little_endian, &is_signed))
                     return NULL;
                 return _PyLong_FromByteArray((unsigned char*)"\\x9A\\xBC\\x41", 3,
                                              little_endian, is_signed);
             """),
            ])
        assert module.from_bytearray(True, False) == 0x41BC9A
        assert module.from_bytearray(True, True) == 0x41BC9A
        assert module.from_bytearray(False, False) == 0x9ABC41
        assert module.from_bytearray(False, True) == -0x6543BF

    def test_fromunicode(self):
        module = self.import_extension('foo', [
            ("from_unicode", "METH_O",
             """
                 Py_UNICODE* u = PyUnicode_AsUnicode(args);
                 return Py_BuildValue("NN",
                     PyLong_FromUnicode(u, 6, 10),
                     PyLong_FromUnicode(u, 6, 16));
             """),
            ])
        # A string with arabic digits. 'BAD' is after the 6th character.
        assert module.from_unicode(u'  1\u0662\u0663\u0664BAD') == (1234, 4660)

    def test_aslong(self):
        module = self.import_extension('foo', [
            ("as_long", "METH_O",
             """
                long n = PyLong_AsLong(args);
                if (n == -1 && PyErr_Occurred()) {
                    return NULL;
                }
                return PyLong_FromLong(n);
             """)])
        assert module.as_long(123) == 123
        assert module.as_long(-1) == -1
        assert module.as_long(1.23) == 1

    def test_strtol(self):
        module = self.import_extension('foo', [
            ("from_str", "METH_NOARGS",
             """
                 const char *str ="  400";
                 char * end;
                 if (400 != PyOS_strtoul(str, &end, 10))
                    return PyLong_FromLong(1);
                 if (str + strlen(str) != end)
                    return PyLong_FromLong(2);
                 if (400 != PyOS_strtol(str, &end, 10))
                    return PyLong_FromLong(3);
                 if (str + strlen(str) != end)
                    return PyLong_FromLong(4);
                 return PyLong_FromLong(0);
             """)])
        assert module.from_str() == 0

    def test_slots(self):
        module = self.import_extension('foo', [
            ("has_sub", "METH_NOARGS",
             """
                PyObject *ret, *obj = PyLong_FromLong(42);
                if (obj->ob_type != &PyLong_Type)
                    ret = PyLong_FromLong(-2);
                else
                {
                    if (obj->ob_type->tp_as_number->nb_subtract)
                        ret = obj->ob_type->tp_as_number->nb_subtract(obj, obj);
                    else
                        ret = PyLong_FromLong(-1);
                }
                Py_DECREF(obj);
                return ret;
             """),
             ("has_pow", "METH_NOARGS",
             """
                PyObject *ret, *obj = PyLong_FromLong(42);
                PyObject *one = PyLong_FromLong(1);
                if (obj->ob_type->tp_as_number->nb_power)
                    ret = obj->ob_type->tp_as_number->nb_power(obj, one, one);
                else
                    ret = PyLong_FromLong(-1);
                Py_DECREF(obj);
                return ret;
             """),])
        assert module.has_sub() == 0
        assert module.has_pow() == 0
