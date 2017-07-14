from rpython.rtyper.lltypesystem import rffi
from pypy.interpreter.error import OperationError
from pypy.module.cpyext.test.test_api import BaseApiTest, raises_w
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.sequence import (
    PySequence_Fast, PySequence_Contains, PySequence_Index,
    PySequence_GetItem, PySequence_SetItem, PySequence_DelItem)

import pytest

class TestSequence(BaseApiTest):
    def test_check(self, space, api):
        assert api.PySequence_Check(space.newlist([]))
        assert not api.PySequence_Check(space.newdict())

    def test_sequence_api(self, space, api):
        w_l = space.wrap([1, 2, 3, 4])
        assert api.PySequence_Fast(w_l, "message") is w_l

        assert space.int_w(api.PySequence_Fast_GET_ITEM(w_l, 1)) == 2
        assert api.PySequence_Fast_GET_SIZE(w_l) == 4

        w_set = space.wrap(set((1, 2, 3, 4)))
        w_seq = api.PySequence_Fast(w_set, "message")
        assert space.type(w_seq) is space.w_list
        assert space.len_w(w_seq) == 4

        w_seq = api.PySequence_Tuple(w_set)
        assert space.type(w_seq) is space.w_tuple
        assert sorted(space.unwrap(w_seq)) == [1, 2, 3, 4]

        w_seq = api.PySequence_List(w_set)
        assert space.type(w_seq) is space.w_list
        assert sorted(space.unwrap(w_seq)) == [1, 2, 3, 4]

    def test_repeat(self, space, api):
        def test(seq, count):
            w_seq = space.wrap(seq)
            w_repeated = api.PySequence_Repeat(w_seq, count)
            assert space.eq_w(w_repeated, space.wrap(seq * count))

        test((1, 2, 3, 4), 3)
        test([1, 2, 3, 4], 3)

    def test_concat(self, space, api):
        w_t1 = space.wrap(range(4))
        w_t2 = space.wrap(range(4, 8))
        assert space.unwrap(api.PySequence_Concat(w_t1, w_t2)) == range(8)

    def test_inplace_concat(self, space, api):
        w_t1 = space.wrap(range(4))
        w_t2 = space.wrap(range(4, 8))
        w_t3 = api.PySequence_InPlaceConcat(w_t1, w_t2)
        assert space.unwrap(w_t3) == range(8)
        assert space.unwrap(w_t1) == range(8)

    def test_inplace_repeat(self, space, api):
        w_t1 = space.wrap(range(2))
        w_t2 = api.PySequence_InPlaceRepeat(w_t1, 3)
        assert space.unwrap(w_t2) == [0, 1, 0, 1, 0, 1]

    def test_exception(self, space):
        message = rffi.str2charp("message")
        with pytest.raises(OperationError) as excinfo:
            PySequence_Fast(space, space.wrap(3), message)
        assert excinfo.value.match(space, space.w_TypeError)
        assert space.str_w(excinfo.value.get_w_value(space)) == "message"
        rffi.free_charp(message)

    def test_get_slice(self, space, api):
        w_t = space.wrap([1, 2, 3, 4, 5])
        assert space.unwrap(api.PySequence_GetSlice(w_t, 2, 4)) == [3, 4]
        assert space.unwrap(api.PySequence_GetSlice(w_t, 1, -1)) == [2, 3, 4]

        assert api.PySequence_DelSlice(w_t, 1, 4) == 0
        assert space.eq_w(w_t, space.wrap([1, 5]))
        assert api.PySequence_SetSlice(w_t, 1, 1, space.wrap((3,))) == 0
        assert space.eq_w(w_t, space.wrap([1, 3, 5]))

    def test_get_slice_fast(self, space, api):
        w_t = space.wrap([1, 2, 3, 4, 5])
        api.PySequence_Fast(w_t, "foo")  # converts
        assert space.unwrap(api.PySequence_GetSlice(w_t, 2, 4)) == [3, 4]
        assert space.unwrap(api.PySequence_GetSlice(w_t, 1, -1)) == [2, 3, 4]

        assert api.PySequence_DelSlice(w_t, 1, 4) == 0
        assert space.eq_w(w_t, space.wrap([1, 5]))
        assert api.PySequence_SetSlice(w_t, 1, 1, space.wrap((3,))) == 0
        assert space.eq_w(w_t, space.wrap([1, 3, 5]))

    def test_iter(self, space, api):
        w_t = space.wrap((1, 2))
        w_iter = api.PySeqIter_New(w_t)
        assert space.unwrap(space.next(w_iter)) == 1
        assert space.unwrap(space.next(w_iter)) == 2
        exc = raises(OperationError, space.next, w_iter)
        assert exc.value.match(space, space.w_StopIteration)

    def test_contains(self, space):
        w_t = space.wrap((1, 'ha'))
        assert PySequence_Contains(space, w_t, space.wrap(u'ha'))
        assert not PySequence_Contains(space, w_t, space.wrap(2))
        with raises_w(space, TypeError):
            PySequence_Contains(space, space.w_None, space.wrap(2))

    def test_setitem(self, space, api):
        w_value = space.wrap(42)

        l = api.PyList_New(1)
        result = api.PySequence_SetItem(l, 0, w_value)
        assert result != -1
        assert space.eq_w(space.getitem(l, space.wrap(0)), w_value)
        with raises_w(space, IndexError):
            PySequence_SetItem(space, l, 3, w_value)

        t = api.PyTuple_New(1)
        api.PyTuple_SetItem(t, 0, l)
        with raises_w(space, TypeError):
            PySequence_SetItem(space, t, 0, w_value)
        with raises_w(space, TypeError):
            PySequence_SetItem(space, space.newdict(), 0, w_value)

    def test_delitem(self, space, api):
        w_l = space.wrap([1, 2, 3, 4])
        result = api.PySequence_DelItem(w_l, 2)
        assert result == 0
        assert space.eq_w(w_l, space.wrap([1, 2, 4]))
        with raises_w(space, IndexError):
            PySequence_DelItem(space, w_l, 3)

    def test_getitem(self, space, api):
        thelist = [8, 7, 6, 5, 4, 3, 2, 1]
        w_l = space.wrap(thelist)
        result = api.PySequence_GetItem(w_l, 4)
        assert space.is_true(space.eq(result, space.wrap(4)))
        result = api.PySequence_ITEM(w_l, 4)
        assert space.is_true(space.eq(result, space.wrap(4)))
        with raises_w(space, IndexError):
            PySequence_GetItem(space, w_l, 9000)

    def test_index(self, space, api):
        thelist = [9, 8, 7, 6, 5, 4, 3, 2, 1]
        w_l = space.wrap(thelist)
        w_tofind = space.wrap(5)

        result = api.PySequence_Index(w_l, w_tofind)
        assert result == thelist.index(5)

        w_tofind = space.wrap(9001)
        with raises_w(space, ValueError):
            PySequence_Index(space, w_l, w_tofind)

        w_gen = space.appexec([], """():
           return (x ** 2 for x in range(40))""")
        w_tofind = space.wrap(16)
        result = api.PySequence_Index(w_gen, w_tofind)
        assert result == 4

class AppTestSetObject(AppTestCpythonExtensionBase):
    def test_sequence_macro_cast(self):
        module = self.import_extension('foo', [
            ("test_macro_cast", "METH_NOARGS",
             """
             PyObject *o = PyList_New(0);
             PyListObject* l;
             PyList_Append(o, o);
             l = (PyListObject*)o;

             PySequence_Fast_GET_ITEM(o, 0);
             PySequence_Fast_GET_ITEM(l, 0);

             PySequence_Fast_GET_SIZE(o);
             PySequence_Fast_GET_SIZE(l);

             PySequence_ITEM(o, 0);
             PySequence_ITEM(l, 0);

             return o;
             """
            )
        ])
class TestCPyListStrategy(BaseApiTest):
    def test_getitem_setitem(self, space, api):
        w_l = space.wrap([1, 2, 3, 4])
        api.PySequence_Fast(w_l, "foo") # converts
        assert space.int_w(space.len(w_l)) == 4
        assert space.int_w(space.getitem(w_l, space.wrap(1))) == 2
        assert space.int_w(space.getitem(w_l, space.wrap(0))) == 1
        e = pytest.raises(OperationError, space.getitem, w_l, space.wrap(15))
        assert "list index out of range" in e.value.errorstr(space)
        assert space.int_w(space.getitem(w_l, space.wrap(-1))) == 4
        space.setitem(w_l, space.wrap(1), space.wrap(13))
        assert space.int_w(space.getitem(w_l, space.wrap(1))) == 13

    def test_manipulations(self, space, api):
        w = space.wrap
        w_l = w([1, 2, 3, 4])

        api.PySequence_Fast(w_l, "foo") # converts
        space.call_method(w_l, 'insert', w(0), w(0))
        assert space.int_w(space.len(w_l)) == 5
        assert space.int_w(space.getitem(w_l, w(3))) == 3

        api.PySequence_Fast(w_l, "foo") # converts
        space.call_method(w_l, 'sort')
        assert space.int_w(space.len(w_l)) == 5
        assert space.int_w(space.getitem(w_l, w(0))) == 0

        api.PySequence_Fast(w_l, "foo") # converts
        w_t = space.wrap(space.fixedview(w_l))
        assert space.int_w(space.len(w_t)) == 5
        assert space.int_w(space.getitem(w_t, w(0))) == 0
        w_l2 = space.wrap(space.listview(w_t))
        assert space.int_w(space.len(w_l2)) == 5
        assert space.int_w(space.getitem(w_l2, w(0))) == 0

        api.PySequence_Fast(w_l, "foo") # converts
        w_sum = space.add(w_l, w_l)
        assert space.int_w(space.len(w_sum)) == 10

        api.PySequence_Fast(w_l, "foo") # converts
        w_prod = space.mul(w_l, space.wrap(2))
        assert space.int_w(space.len(w_prod)) == 10

        api.PySequence_Fast(w_l, "foo") # converts
        w_l.inplace_mul(2)
        assert space.int_w(space.len(w_l)) == 10


class AppTestSequenceObject(AppTestCpythonExtensionBase):
    def test_fast(self):
        module = self.import_extension('foo', [
            ("test_fast_sequence", "METH_VARARGS",
             """
                int size, i;
                PyTypeObject * common_type;
                PyObject *foo, **objects;
                PyObject * seq = PyTuple_GetItem(args, 0);
                /* XXX assert it is a tuple */
                if (seq == NULL)
                    Py_RETURN_NONE;
                foo = PySequence_Fast(seq, "some string");
                objects = PySequence_Fast_ITEMS(foo);
                size = PySequence_Fast_GET_SIZE(seq);
                common_type = size > 0 ? Py_TYPE(objects[0]) : NULL;
                for (i = 1; i < size; ++i) {
                    if (Py_TYPE(objects[i]) != common_type) {
                        common_type = NULL;
                        break;
                    }
                }
                Py_DECREF(foo);
                Py_DECREF(common_type);
                return PyBool_FromLong(1);
             """)])
        s = [1, 2, 3, 4]
        assert module.test_fast_sequence(s[0:-1])
        assert module.test_fast_sequence(s[::-1])

    def test_fast_keyerror(self):
        module = self.import_extension('foo', [
            ("test_fast_sequence", "METH_VARARGS",
             """
                PyObject *foo;
                PyObject * seq = PyTuple_GetItem(args, 0);
                if (seq == NULL)
                    Py_RETURN_NONE;
                foo = PySequence_Fast(seq, "Could not convert object to sequence");
                if (foo != NULL)
                {
                    return foo;
                }
                if (PyErr_ExceptionMatches(PyExc_KeyError)) {
                    PyErr_Clear();
                    return PyBool_FromLong(1);
                }
                return NULL;
             """)])
        class Map(object):
            def __len__(self):
                return 1

            def __getitem__(self, index):
                raise KeyError()

        assert module.test_fast_sequence(Map()) is True

