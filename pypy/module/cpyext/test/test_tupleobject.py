import py

from pypy.module.cpyext.pyobject import PyObject, PyObjectP, make_ref, from_ref
from pypy.module.cpyext.test.test_api import BaseApiTest, raises_w
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib.debug import FatalError
from pypy.module.cpyext.tupleobject import (
    PyTupleObject, PyTuple_Check, PyTuple_SetItem, PyTuple_Size)


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
        py_tuple = api.PyTuple_New(1)
        py.test.raises(FatalError, from_ref, space, py_tuple)
        api.Py_DecRef(py_tuple)

    def test_tuple_resize(self, space, api):
        w_42 = space.wrap(42)
        w_43 = space.wrap(43)
        w_44 = space.wrap(44)
        ar = lltype.malloc(PyObjectP.TO, 1, flavor='raw')

        py_tuple = api.PyTuple_New(3)
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
        api.Py_DecRef(ar[0])

        py_tuple = api.PyTuple_New(3)
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
        api.Py_DecRef(ar[0])

        lltype.free(ar, flavor='raw')

    def test_setitem(self, space, api):
        py_tuple = api.PyTuple_New(2)
        api.PyTuple_SetItem(py_tuple, 0, make_ref(space, space.wrap(42)))
        api.PyTuple_SetItem(py_tuple, 1, make_ref(space, space.wrap(43)))

        w_tuple = from_ref(space, py_tuple)
        assert space.eq_w(w_tuple, space.newtuple([space.wrap(42),
                                                   space.wrap(43)]))
        api.Py_DecRef(py_tuple)

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
#ifdef PYPY_VERSION
                // PyPy starts even empty tuples with a refcount of 1.
                const int initial_item_refcount = 1;
#else
                // CPython can cache ().
                const int initial_item_refcount = item->ob_refcnt;
#endif  // PYPY_VERSION
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
