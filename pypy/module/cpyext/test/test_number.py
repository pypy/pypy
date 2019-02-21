import pytest
from rpython.rtyper.lltypesystem import lltype
from pypy.interpreter.error import OperationError
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.number import (
    PyIndex_Check, PyNumber_Check, PyNumber_Long,
    PyNumber_Index, PyNumber_Add,
    PyNumber_Multiply, PyNumber_InPlaceMultiply, PyNumber_Absolute,
    PyNumber_Power, PyNumber_InPlacePower)
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

    def test_number_long2(self, space):
        w_l = PyNumber_Long(space, space.wraplong(123L))
        assert PyLong_CheckExact(space, w_l)
        w_l = PyNumber_Long(space, space.wrap(2 << 65))
        assert PyLong_CheckExact(space, w_l)
        w_l = PyNumber_Long(space, space.wrap(42.3))
        assert PyLong_CheckExact(space, w_l)
        w_l = PyNumber_Long(space, space.wrap("42"))
        assert PyLong_CheckExact(space, w_l)

    def test_number_index(self, space):
        w_l = PyNumber_Index(space, space.wraplong(123L))
        assert PyLong_CheckExact(space, w_l)
        with pytest.raises(OperationError):
            PyNumber_Index(space, space.wrap(42.3))

    def test_numbermethods(self, space, api):
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
    def test_PyNumber_Check(self):
        mod = self.import_extension('foo', [
            ("test_PyNumber_Check", "METH_VARARGS",
             '''
                PyObject *obj = PyTuple_GET_ITEM(args, 0);
                int val = PyNumber_Check(obj);
                return PyLong_FromLong(val);
            ''')])
        val = mod.test_PyNumber_Check(10)
        assert val == 1
