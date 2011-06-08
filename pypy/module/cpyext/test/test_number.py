from pypy.rpython.lltypesystem import rffi, lltype
from pypy.interpreter.error import OperationError
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext import sequence

class TestIterator(BaseApiTest):
    def test_check(self, space, api):
        assert api.PyIndex_Check(space.wrap(12))
        assert api.PyIndex_Check(space.wrap(-12L))
        assert not api.PyIndex_Check(space.wrap(12.1))
        assert not api.PyIndex_Check(space.wrap('12'))

        assert api.PyNumber_Check(space.wrap(12))
        assert api.PyNumber_Check(space.wrap(-12L))
        assert api.PyNumber_Check(space.wrap(12.1))
        assert not api.PyNumber_Check(space.wrap('12'))
        assert not api.PyNumber_Check(space.wrap(1+3j))

    def test_number_long(self, space, api):
        w_l = api.PyNumber_Long(space.wrap(123))
        assert api.PyLong_CheckExact(w_l)

    def test_number_int(self, space, api):
        w_l = api.PyNumber_Int(space.wrap(123L))
        assert api.PyInt_CheckExact(w_l)
        w_l = api.PyNumber_Int(space.wrap(2 << 65))
        assert api.PyLong_CheckExact(w_l)
        w_l = api.PyNumber_Int(space.wrap(42.3))
        assert api.PyInt_CheckExact(w_l)

    def test_number_index(self, space, api):
        w_l = api.PyNumber_Index(space.wrap(123L))
        assert api.PyLong_CheckExact(w_l)
        w_l = api.PyNumber_Index(space.wrap(42.3))
        assert w_l is None
        api.PyErr_Clear()

    def test_numbermethods(self, space, api):
        assert "ab" == space.unwrap(
            api.PyNumber_Add(space.wrap("a"), space.wrap("b")))
        assert "aaa" == space.unwrap(
            api.PyNumber_Multiply(space.wrap("a"), space.wrap(3)))

        w_l = space.newlist([1, 2, 3])
        w_l2 = api.PyNumber_Multiply(w_l, space.wrap(3))
        assert api.PyObject_Size(w_l2) == 9
        assert api.PyObject_Size(w_l) == 3

        w_l3 = api.PyNumber_InPlaceMultiply(w_l, space.wrap(3))
        assert api.PyObject_Size(w_l) == 9
        assert w_l3 is w_l

        # unary function
        assert 9 == space.unwrap(api.PyNumber_Absolute(space.wrap(-9)))

        # power
        assert 9 == space.unwrap(
            api.PyNumber_Power(space.wrap(3), space.wrap(2), space.w_None))
        assert 4 == space.unwrap(
            api.PyNumber_Power(space.wrap(3), space.wrap(2), space.wrap(5)))
        assert 9 == space.unwrap(
            api.PyNumber_InPlacePower(space.wrap(3), space.wrap(2), space.w_None))
