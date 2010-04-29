import py
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.state import State
from pypy.module.cpyext.pyobject import make_ref, add_borrowed_object


class TestBorrowing(BaseApiTest):
    def test_borrowing(self, space, api):
        state = space.fromcache(State)
        w_int = space.wrap(1)
        w_tuple = space.newtuple([w_int])
        api.Py_IncRef(w_tuple)
        api.register_container(w_tuple)
        one_pyo = make_ref(space, w_int, borrowed=True)
        add_borrowed_object(space, one_pyo)
        print state.borrowed_objects
        api.Py_DecRef(w_tuple)
        state.print_refcounts()
        py.test.raises(AssertionError, api.Py_DecRef, one_pyo)

class AppTestBorrow(AppTestCpythonExtensionBase):
    def test_tuple_borrowing(self):
        module = self.import_extension('foo', [
            ("test_borrowing", "METH_NOARGS",
             """
                PyObject *t = PyTuple_New(1);
                PyObject *f = PyFloat_FromDouble(42.0);
                PyObject *g = NULL;
                printf("Refcnt1: %i\\n", f->ob_refcnt);
                PyTuple_SetItem(t, 0, f); // steals reference
                printf("Refcnt2: %i\\n", f->ob_refcnt);
                f = PyTuple_GetItem(t, 0); // borrows reference
                printf("Refcnt3: %i\\n", f->ob_refcnt);
                g = PyTuple_GetItem(t, 0); // borrows reference again
                printf("Refcnt4: %i\\n", f->ob_refcnt);
                printf("COMPARE: %i\\n", f == g);
                Py_DECREF(t);
                Py_RETURN_TRUE;
             """),
            ])
        assert module.test_borrowing() # the test should not leak

