import py
import pytest
from rpython.rtyper.lltypesystem import lltype
from pypy.interpreter.error import OperationError
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.pyobject import (
    PyObjectP, from_ref, make_ref, decref)
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.number import (
    PyIndex_Check, PyNumber_Check, PyNumber_Long, PyNumber_Int,
    PyNumber_Index, PyNumber_Coerce, PyNumber_CoerceEx, PyNumber_Add,
    PyNumber_Multiply, PyNumber_InPlaceMultiply, PyNumber_Absolute,
    PyNumber_Power, PyNumber_InPlacePower)
from pypy.module.cpyext.intobject import PyInt_CheckExact
from pypy.module.cpyext.longobject import PyLong_CheckExact
from pypy.module.cpyext.object import PyObject_Size

class TestIterator(BaseApiTest):
    def test_check(self, space):
        assert PyIndex_Check(space, space.wrap(12))
        assert PyIndex_Check(space, space.wraplong(-12L))
        assert not PyIndex_Check(space, space.wrap(12.1))
        assert not PyIndex_Check(space, space.wrap('12'))

        assert PyNumber_Check(space, space.wrap(12))
        assert PyNumber_Check(space, space.wraplong(-12L))
        assert PyNumber_Check(space, space.wrap(12.1))
        assert not PyNumber_Check(space, space.wrap('12'))
        assert PyNumber_Check(space, space.wrap(1 + 3j))

    def test_number_long(self, space):
        w_l = PyNumber_Long(space, space.wrap(123))
        assert PyLong_CheckExact(space, w_l)
        w_l = PyNumber_Long(space, space.wrap("123"))
        assert PyLong_CheckExact(space, w_l)

    def test_number_int(self, space):
        w_l = PyNumber_Int(space, space.wraplong(123L))
        assert PyInt_CheckExact(space, w_l)
        w_l = PyNumber_Int(space, space.wrap(2 << 65))
        assert PyLong_CheckExact(space, w_l)
        w_l = PyNumber_Int(space, space.wrap(42.3))
        assert PyInt_CheckExact(space, w_l)
        w_l = PyNumber_Int(space, space.wrap("42"))
        assert PyInt_CheckExact(space, w_l)

    def test_number_index(self, space):
        w_l = PyNumber_Index(space, space.wraplong(123L))
        assert PyLong_CheckExact(space, w_l)
        with pytest.raises(OperationError):
            PyNumber_Index(space, space.wrap(42.3))

    def test_coerce(self, space):
        w_obj1 = space.wrap(123)
        w_obj2 = space.wrap(456.789)
        p1 = make_ref(space, w_obj1)
        p2 = make_ref(space, w_obj2)
        pp1 = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        pp1[0] = p1
        pp2 = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        pp2[0] = p2
        assert PyNumber_Coerce(space, pp1, pp2) == 0
        assert space.str_w(space.repr(from_ref(space, pp1[0]))) == '123.0'
        assert space.str_w(space.repr(from_ref(space, pp2[0]))) == '456.789'
        #
        # We need to decref twice because PyNumber_Coerce does an incref and
        # possibly changes the content of pp1 and pp2
        decref(space, p1)
        decref(space, pp1[0])
        decref(space, p2)
        decref(space, pp2[0])
        lltype.free(pp1, flavor='raw')
        lltype.free(pp2, flavor='raw')

    def test_number_coerce_ex(self, space):
        pl = make_ref(space, space.wrap(123))
        pf = make_ref(space, space.wrap(42.))
        ppl = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        ppf = lltype.malloc(PyObjectP.TO, 1, flavor='raw')
        ppl[0] = pl
        ppf[0] = pf

        ret = PyNumber_CoerceEx(space, ppl, ppf)
        assert ret == 0

        w_res = from_ref(space, ppl[0])

        assert space.isinstance_w(w_res, space.w_float)
        assert space.unwrap(w_res) == 123.
        decref(space, pl)
        decref(space, pf)
        decref(space, ppl[0])
        decref(space, ppf[0])
        lltype.free(ppl, flavor='raw')
        lltype.free(ppf, flavor='raw')

    def test_numbermethods(self, space):
        assert "ab" == space.unwrap(
            PyNumber_Add(space, space.wrap("a"), space.wrap("b")))
        assert "aaa" == space.unwrap(
            PyNumber_Multiply(space, space.wrap("a"), space.wrap(3)))

        w_l = space.newlist([1, 2, 3])
        w_l2 = PyNumber_Multiply(space, w_l, space.wrap(3))
        assert PyObject_Size(space, w_l2) == 9
        assert PyObject_Size(space, w_l) == 3

        w_l3 = PyNumber_InPlaceMultiply(space, w_l, space.wrap(3))
        assert PyObject_Size(space, w_l) == 9
        assert w_l3 is w_l

        # unary function
        assert 9 == space.unwrap(PyNumber_Absolute(space, space.wrap(-9)))

        # power
        assert 9 == space.unwrap(
            PyNumber_Power(space, space.wrap(3), space.wrap(2), space.w_None))
        assert 4 == space.unwrap(
            PyNumber_Power(space, space.wrap(3), space.wrap(2), space.wrap(5)))
        assert 9 == space.unwrap(
            PyNumber_InPlacePower(space, space.wrap(3), space.wrap(2), space.w_None))

class AppTestCNumber(AppTestCpythonExtensionBase):
    def test_app_coerce(self):
        if self.runappdirect:
            py.test.xfail('crashes with TypeError')
        mod = self.import_extension('foo', [
            ("test_fail", "METH_NOARGS",
             '''
                PyObject * hello = PyString_FromString("hello");
                PyObject * float1 = PyFloat_FromDouble(1.0);
                int retVal = PyNumber_Coerce(&hello, &float1);
                Py_DECREF(hello);
                Py_DECREF(float1);
                return PyInt_FromLong(retVal);
            '''),
            ("test", "METH_NOARGS",
             '''
                PyObject * float1p = PyFloat_FromDouble(1.0);
                PyObject * int3p   = PyInt_FromLong(3);
                PyObject * tupl = PyTuple_New(2);
                PyObject float1 = *float1p;
                PyObject int3 = *int3p;
                int retVal = PyNumber_CoerceEx(&int3p, &float1p);
                if (retVal == 0)
                {
                    PyTuple_SET_ITEM(tupl, 0, int3p);
                    PyTuple_SET_ITEM(tupl, 1, float1p);
                }
                Py_DECREF(&int3);
                Py_DECREF(&float1);
                Py_DECREF(int3p);
                Py_DECREF(float1p);
                return tupl;
            ''')])
        assert mod.test_fail() == -1
        '''tupl = mod.test()
        assert tupl[0] == 3.
        assert tupl[1] == 1.
        assert isinstance(tupl[0], float)'''

    def test_PyNumber_Check(self):
        mod = self.import_extension('foo', [
            ("test_PyNumber_Check", "METH_VARARGS",
             '''
                PyObject *obj = PyTuple_GET_ITEM(args, 0);
                int val = PyNumber_Check(obj);
                return PyInt_FromLong(val);
            ''')])
        val = mod.test_PyNumber_Check(10)
        assert val == 1

    def test_number_tobase(self):
        import sys
        mod = self.import_extension('foo', [
            ("pynumber_tobase", "METH_VARARGS",
            """
                PyObject *obj;
                int base;
                if (!PyArg_ParseTuple(args, "Oi:pynumber_tobase",
                                      &obj, &base)) {
                    return NULL;
                }
                return PyNumber_ToBase(obj, base);
            """)])
        assert mod.pynumber_tobase(123, 2) == '0b1111011'
        assert mod.pynumber_tobase(123, 8) == '0o173'
        assert mod.pynumber_tobase(123, 10) == '123'
        assert mod.pynumber_tobase(123, 16) == '0x7b'
        assert mod.pynumber_tobase(-123, 2) == '-0b1111011'
        assert mod.pynumber_tobase(-123, 8) == '-0o173'
        assert mod.pynumber_tobase(-123, 10) == '-123'
        assert mod.pynumber_tobase(-123, 16) == '-0x7b'
        try:
            mod.pynumber_tobase(123.0, 10)
        except TypeError:
            pass
        else:
            assert False, 'expected TypeError'
        try:
            mod.pynumber_tobase('123', 10)
        except TypeError:
            pass
        else:
            assert False, 'expected TypeError'
        if 'PyPy' in sys.version or sys.version_info >= (3,7):
            # bpo 38643
            try:
                mod.pynumber_tobase(123, 0)
            except ValueError:
                pass
            else:
                assert False, 'expected TypeError'
