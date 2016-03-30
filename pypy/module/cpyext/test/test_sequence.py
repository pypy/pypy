from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.interpreter.error import OperationError
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext import sequence
import py.test

class TestSequence(BaseApiTest):
    def test_sequence(self, space, api):
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

    def test_exception(self, space, api):
        message = rffi.str2charp("message")
        assert not api.PySequence_Fast(space.wrap(3), message)
        assert api.PyErr_Occurred() is space.w_TypeError
        api.PyErr_Clear()

        exc = raises(OperationError, sequence.PySequence_Fast,
                     space, space.wrap(3), message)
        assert exc.value.match(space, space.w_TypeError)
        assert space.str_w(exc.value.get_w_value(space)) == "message"
        rffi.free_charp(message)

    def test_get_slice(self, space, api):
        w_t = space.wrap([1, 2, 3, 4, 5])
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

    def test_contains(self, space, api):
        w_t = space.wrap((1, 'ha'))
        assert api.PySequence_Contains(w_t, space.wrap(u'ha'))
        assert not api.PySequence_Contains(w_t, space.wrap(2))
        assert api.PySequence_Contains(space.w_None, space.wrap(2)) == -1
        assert api.PyErr_Occurred()
        api.PyErr_Clear()

    def test_setitem(self, space, api):
        w_value = space.wrap(42)

        l = api.PyList_New(1)
        result = api.PySequence_SetItem(l, 0, w_value)
        assert result != -1
        assert space.eq_w(space.getitem(l, space.wrap(0)), w_value)

        self.raises(space, api, IndexError, api.PySequence_SetItem,
                    l, 3, w_value)

        t = api.PyTuple_New(1)
        api.PyTuple_SetItem(t, 0, l)
        self.raises(space, api, TypeError, api.PySequence_SetItem,
                    t, 0, w_value)

        self.raises(space, api, TypeError, api.PySequence_SetItem,
                    space.newdict(), 0, w_value)

    def test_delitem(self, space, api):
        w_l = space.wrap([1, 2, 3, 4])

        result = api.PySequence_DelItem(w_l, 2)
        assert result == 0
        assert space.eq_w(w_l, space.wrap([1, 2, 4]))

        self.raises(space, api, IndexError, api.PySequence_DelItem,
                    w_l, 3)

    def test_getitem(self, space, api):
        thelist = [8, 7, 6, 5, 4, 3, 2, 1]
        w_l = space.wrap(thelist)

        result = api.PySequence_GetItem(w_l, 4)
        assert space.is_true(space.eq(result, space.wrap(4)))

        result = api.PySequence_ITEM(w_l, 4)
        assert space.is_true(space.eq(result, space.wrap(4)))

        self.raises(space, api, IndexError, api.PySequence_GetItem, w_l, 9000)

    def test_index(self, space, api):
        thelist = [9, 8, 7, 6, 5, 4, 3, 2, 1]
        w_l = space.wrap(thelist)
        w_tofind = space.wrap(5)

        result = api.PySequence_Index(w_l, w_tofind)
        assert result == thelist.index(5)

        w_tofind = space.wrap(9001)
        result = api.PySequence_Index(w_l, w_tofind)
        assert result == -1
        assert api.PyErr_Occurred() is space.w_ValueError
        api.PyErr_Clear()

        w_gen = space.appexec([], """():
           return (x ** 2 for x in range(40))""")
        w_tofind = space.wrap(16)
        result = api.PySequence_Index(w_gen, w_tofind)
        assert result == 4

class TestCPyListStrategy(BaseApiTest):
    def test_getitem_setitem(self, space, api):
        w_l = space.wrap([1, 2, 3, 4])
        api.PySequence_Fast(w_l, "foo") # converts
        assert space.int_w(space.len(w_l)) == 4
        assert space.int_w(space.getitem(w_l, space.wrap(1))) == 2
        assert space.int_w(space.getitem(w_l, space.wrap(0))) == 1
        e = py.test.raises(OperationError, space.getitem, w_l, space.wrap(15))
        assert "list index out of range" in e.exconly()
        assert space.int_w(space.getitem(w_l, space.wrap(-1))) == 4
        space.setitem(w_l, space.wrap(1), space.wrap(13))
        assert space.int_w(space.getitem(w_l, space.wrap(1))) == 13


class XAppTestSequenceObject(AppTestCpythonExtensionBase):
    def test_sequenceobject(self):
        module = self.import_extension('foo', [
            ("test_fast_sequence", "METH_VARARGS",
             """
                PyObject * o = PyTuple_GetItem(args, 0);
                /* XXX assert it is a tuple */
                PyObject *foo = PySequence_Fast(o, "some string");
                PyObject ** res = PySequence_Fast_ITEMS(foo);
                /* XXX do some kind of test on res */
                /* XXX now what? who manages res's refcount? */
                return PyBool_FromLong(1);
             """)])
        assert module.test_fast_sequence([1, 2, 3, 4])

