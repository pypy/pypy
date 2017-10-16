import py

from pypy.module.cpyext.pyobject import PyObject, PyObjectP, make_ref, from_ref, decref, as_pyobj
from pypy.module.cpyext.test.test_api import BaseApiTest, raises_w
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib.debug import FatalError
from pypy.module.cpyext.tupleobject import (
    PyTupleObject, PyTuple_Check, PyTuple_SetItem, PyTuple_Size,
    tuple_from_args_w)
from pypy.module.cpyext.state import State

class TestTupleObject(BaseApiTest):

    def test_tupleobject(self, space):
        assert not PyTuple_Check(space, space.w_None)
        with raises_w(space, SystemError):
            PyTuple_SetItem(space, space.w_None, 0, space.w_None)
        atuple = space.newtuple([space.wrap(0), space.wrap(1),
                                 space.wrap('yay')])
        assert PyTuple_Size(space, atuple) == 3
        with raises_w(space, SystemError):
            PyTuple_Size(space, space.newlist([]))

    def test_tuple_realize_refuses_nulls(self, space, api):
        state = space.fromcache(State)
        py_tuple = state.C.PyTuple_New(1)
        py.test.raises(FatalError, from_ref, space, py_tuple)
        decref(space, py_tuple)

    def test_freelist(self, space, api):
        state = space.fromcache(State)
        # check that we don't cache the empty tuple
        py_a = state.C.PyTuple_New(0)
        py_b = state.C.PyTuple_New(0)
        assert py_a != py_b
        assert py_a.c_ob_refcnt == 1
        assert py_b.c_ob_refcnt == 1
        decref(space, py_a)
        decref(space, py_b)
        #
        # check that the freelist is working
        py_c = state.C.PyTuple_New(0)
        assert py_c == py_b
        decref(space, py_c)

    def test_empty_tuple_as_pyobj(self, space, api):
        state = space.fromcache(State)
        w_a = space.newtuple([])
        w_b = space.newtuple([])
        assert w_a is not w_b
        py_a = as_pyobj(space, w_a)
        py_b = as_pyobj(space, w_b)
        assert py_a != py_b

    def test_PyTuple_New_initialize_pypy_link(self, space, api):
        from rpython.rlib.rawrefcount import _collect
        state = space.fromcache(State)
        # see object.c:_pypy_rawrefcount_w_marker_deallocating
        MARKER = 0xDEADFFF
        #
        # first: create a pytuple, attach a w_obj, decref the pytuple and let
        # the GC to collect the w_obj: this way, c_ob_pypy_link is set to
        # w_marker_deallocating
        py_a = state.C.PyTuple_New(0)
        assert py_a.c_ob_pypy_link == 0
        w_a = from_ref(space, py_a)
        assert py_a.c_ob_pypy_link != 0
        decref(space, py_a)
        w_a = None
        _collect()
        assert py_a.c_ob_pypy_link == MARKER
        #
        # second: create another tuple, which will reuse the same memory as
        # before thanks to the freelist. Check that c_ob_pypy_link has been
        # initialized to 0.
        py_b = state.C.PyTuple_New(0)
        assert py_b == py_a
        assert py_b.c_ob_pypy_link == 0

    def test_tuple_from_args_w(self, space, api):
        args_w = [space.newint(i) for i in (40, 41, 42)]
        py_tuple = tuple_from_args_w(space, args_w)
        assert py_tuple.c_ob_refcnt == 1
        assert api.PyTuple_Size(py_tuple) == 3
        py_items = [api.PyTuple_GetItem(py_tuple, i) for i in range(3)]
        items = [api.PyInt_AsLong(py_obj) for py_obj in py_items]
        assert items == [40, 41, 42]
        decref(space, py_tuple)

    def test_tuple_resize(self, space, api):
        state = space.fromcache(State)
        w_42 = space.wrap(42)
        w_43 = space.wrap(43)
        w_44 = space.wrap(44)
        ar = lltype.malloc(PyObjectP.TO, 1, flavor='raw')

        py_tuple = state.C.PyTuple_New(3)
        # inside py_tuple is an array of "PyObject *" items which each hold
        # a reference
        rffi.cast(PyTupleObject, py_tuple).c_ob_item[0] = make_ref(space, w_42)
        rffi.cast(PyTupleObject, py_tuple).c_ob_item[1] = make_ref(space, w_43)
        ar[0] = py_tuple
        api._PyTuple_Resize(ar, 2)
        w_tuple = from_ref(space, ar[0])
        assert space.int_w(space.len(w_tuple)) == 2
        assert space.int_w(space.getitem(w_tuple, space.wrap(0))) == 42
        assert space.int_w(space.getitem(w_tuple, space.wrap(1))) == 43
        decref(space, ar[0])

        py_tuple = state.C.PyTuple_New(3)
        rffi.cast(PyTupleObject, py_tuple).c_ob_item[0] = make_ref(space, w_42)
        rffi.cast(PyTupleObject, py_tuple).c_ob_item[1] = make_ref(space, w_43)
        rffi.cast(PyTupleObject, py_tuple).c_ob_item[2] = make_ref(space, w_44)
        ar[0] = py_tuple
        api._PyTuple_Resize(ar, 10)
        assert api.PyTuple_Size(ar[0]) == 10
        for i in range(3, 10):
            rffi.cast(PyTupleObject, ar[0]).c_ob_item[i] = make_ref(
                space, space.wrap(42 + i))
        w_tuple = from_ref(space, ar[0])
        assert space.int_w(space.len(w_tuple)) == 10
        for i in range(10):
            assert space.int_w(space.getitem(w_tuple, space.wrap(i))) == 42 + i
        decref(space, ar[0])

        lltype.free(ar, flavor='raw')

    def test_setitem(self, space, api):
        state = space.fromcache(State)
        py_tuple = state.C.PyTuple_New(2)
        api.PyTuple_SetItem(py_tuple, 0, make_ref(space, space.wrap(42)))
        api.PyTuple_SetItem(py_tuple, 1, make_ref(space, space.wrap(43)))

        w_tuple = from_ref(space, py_tuple)
        assert space.eq_w(w_tuple, space.newtuple([space.wrap(42),
                                                   space.wrap(43)]))
        decref(space, py_tuple)

    def test_getslice(self, space, api):
        w_tuple = space.newtuple([space.wrap(i) for i in range(10)])
        w_slice = api.PyTuple_GetSlice(w_tuple, 3, -3)
        assert space.eq_w(w_slice,
                          space.newtuple([space.wrap(i) for i in range(3, 7)]))


class AppTestTuple(AppTestCpythonExtensionBase):
    def test_refcounts(self):
        module = self.import_extension('foo', [
            ("run", "METH_NOARGS",
             """
                PyObject *item = PyTuple_New(0);
                PyObject *t = PyTuple_New(1);
                // the empty tuple is cached, so we can't assume its refcnt is 1
                const Py_ssize_t initial_item_refcount = item->ob_refcnt;

                if (t->ob_refcnt != 1 || item->ob_refcnt != initial_item_refcount) {
                    PyErr_SetString(PyExc_SystemError, "bad initial refcnt");
                    return NULL;
                }

                PyTuple_SetItem(t, 0, item);
                if (t->ob_refcnt != 1) {
                    PyErr_SetString(PyExc_SystemError, "SetItem: t refcnt != 1");
                    return NULL;
                }
                if (item->ob_refcnt != initial_item_refcount) {
                    PyErr_SetString(PyExc_SystemError, "GetItem: item refcnt != initial_item_refcount");
                    return NULL;
                }

                if (PyTuple_GetItem(t, 0) != item ||
                    PyTuple_GetItem(t, 0) != item) {
                    PyErr_SetString(PyExc_SystemError, "GetItem: bogus item");
                    return NULL;
                }

                if (t->ob_refcnt != 1) {
                    PyErr_SetString(PyExc_SystemError, "GetItem: t refcnt != 1");
                    return NULL;
                }
                if (item->ob_refcnt != initial_item_refcount) {
                    PyErr_SetString(PyExc_SystemError, "GetItem: item refcnt != initial_item_refcount");
                    return NULL;
                }
                return t;
             """),
            ])
        x = module.run()
        assert x == ((),)

    def test_refcounts_more(self):
        module = self.import_extension('foo', [
            ("run", "METH_NOARGS",
             """
                long prev;
                PyObject *t = PyTuple_New(1);
                prev = Py_True->ob_refcnt;
                Py_INCREF(Py_True);
                PyTuple_SetItem(t, 0, Py_True);
                if (Py_True->ob_refcnt != prev + 1) {
                    PyErr_SetString(PyExc_SystemError,
                        "SetItem: Py_True refcnt != prev + 1");
                    return NULL;
                }
                Py_DECREF(t);
                if (Py_True->ob_refcnt != prev) {
                    PyErr_SetString(PyExc_SystemError,
                        "after: Py_True refcnt != prev");
                    return NULL;
                }
                Py_INCREF(Py_None);
                return Py_None;
             """),
            ])
        module.run()

    def test_tuple_subclass(self):
        module = self.import_module(name='foo')
        a = module.TupleLike(range(100, 400, 100))
        assert module.is_TupleLike(a) == 1
        assert isinstance(a, tuple)
        assert issubclass(type(a), tuple)
        assert list(a) == range(100, 400, 100)
        assert list(a) == range(100, 400, 100)
        assert list(a) == range(100, 400, 100)

    def test_setitem(self):
        module = self.import_extension('foo', [
            ("set_after_use", "METH_O",
             """
                PyObject *t2, *tuple = PyTuple_New(1);
                PyObject * one = PyLong_FromLong(1);
                int res;
                Py_INCREF(one);
                res = PyTuple_SetItem(tuple, 0, one);
                if (res != 0)
                {
                    Py_DECREF(one);
                    Py_DECREF(tuple);
                    return NULL;
                }
                Py_INCREF(args);
                res = PyTuple_SetItem(tuple, 0, args);
                if (res != 0)
                {
                    Py_DECREF(tuple);
                    return NULL;
                }
                /* Do something that uses the tuple, but does not incref */
                t2 = PyTuple_GetSlice(tuple, 0, 1);
                Py_DECREF(t2);
                res = PyTuple_SetItem(tuple, 0, one);
                if (res != 0)
                {
                    Py_DECREF(tuple);
                    return NULL;
                }
                Py_DECREF(tuple);
                Py_INCREF(Py_None);
                return Py_None;
             """),
            ])
        import sys
        s = 'abc'
        if '__pypy__' in sys.builtin_module_names:
            raises(SystemError, module.set_after_use, s)
        else:
            module.set_after_use(s)
