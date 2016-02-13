import py

from pypy.module.cpyext.pyobject import PyObject, PyObjectP, make_ref, from_ref
from pypy.module.cpyext.pyobject import as_pyobj
from pypy.module.cpyext.tupleobject import PyTupleObject
from pypy.module.cpyext.test.test_api import BaseApiTest
from rpython.rtyper.lltypesystem import rffi, lltype


class TestTupleObject(BaseApiTest):

    def test_tupleobject(self, space, api):
        assert not api.PyTuple_Check(space.w_None)
        assert api.PyTuple_SetItem(space.w_None, 0, space.w_None) == -1
        atuple = space.newtuple([space.wrap(0), space.wrap(1),
                                 space.wrap('yay')])
        assert api.PyTuple_Size(atuple) == 3
        #assert api.PyTuple_GET_SIZE(atuple) == 3  --- now a C macro
        raises(TypeError, api.PyTuple_Size(space.newlist([])))
        api.PyErr_Clear()
    
    def test_tuple_resize(self, space, api):
        w_42 = space.wrap(42)
        ar = lltype.malloc(PyObjectP.TO, 1, flavor='raw')

        py_tuple = api.PyTuple_New(3)
        rffi.cast(PyTupleObject, py_tuple).c_ob_item[0] = as_pyobj(space, w_42)
        ar[0] = py_tuple
        api._PyTuple_Resize(ar, 2)
        w_tuple = from_ref(space, ar[0])
        assert space.int_w(space.len(w_tuple)) == 2
        assert space.int_w(space.getitem(w_tuple, space.wrap(0))) == 42
        api.Py_DecRef(ar[0])

        py_tuple = api.PyTuple_New(3)
        rffi.cast(PyTupleObject, py_tuple).c_ob_item[0] = as_pyobj(space, w_42)
        ar[0] = py_tuple
        api._PyTuple_Resize(ar, 10)
        w_tuple = from_ref(space, ar[0])
        assert space.int_w(space.len(w_tuple)) == 10
        assert space.int_w(space.getitem(w_tuple, space.wrap(0))) == 42
        api.Py_DecRef(ar[0])

        lltype.free(ar, flavor='raw')

    def test_setitem(self, space, api):
        atuple = space.newtuple([space.wrap(0), space.wrap("hello")])
        assert api.PyTuple_Size(atuple) == 2
        assert space.eq_w(space.getitem(atuple, space.wrap(0)), space.wrap(0))
        assert space.eq_w(space.getitem(atuple, space.wrap(1)), space.wrap("hello"))
        w_obj = space.wrap(1)
        api.Py_IncRef(w_obj)
        api.PyTuple_SetItem(atuple, 1, w_obj)
        assert api.PyTuple_Size(atuple) == 2
        assert space.eq_w(space.getitem(atuple, space.wrap(0)), space.wrap(0))
        assert space.eq_w(space.getitem(atuple, space.wrap(1)), space.wrap(1))

    def test_getslice(self, space, api):
        w_tuple = space.newtuple([space.wrap(i) for i in range(10)])
        w_slice = api.PyTuple_GetSlice(w_tuple, 3, -3)
        assert space.eq_w(w_slice,
                          space.newtuple([space.wrap(i) for i in range(3, 7)]))

