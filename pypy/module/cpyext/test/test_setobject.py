import py

from pypy.module.cpyext.pyobject import PyObject, PyObjectP, make_ref, from_ref
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from rpython.rtyper.lltypesystem import rffi, lltype


class TestTupleObject(BaseApiTest):
    def test_setobj(self, space, api):
        assert not api.PySet_Check(space.w_None)
        assert api.PySet_Add(space.w_None, space.w_None) == -1
        api.PyErr_Clear()
        w_set = space.call_function(space.w_set)
        space.call_method(w_set, 'update', space.wrap([1,2,3,4]))
        assert api.PySet_Size(w_set) == 4
        assert api.PySet_GET_SIZE(w_set) == 4
        raises(TypeError, api.PySet_Size(space.newlist([])))
        api.PyErr_Clear()

    def test_set_add_discard(self, space, api):
        w_set = api.PySet_New(None)
        assert api.PySet_Size(w_set) == 0
        w_set = api.PySet_New(space.wrap([1,2,3,4]))
        assert api.PySet_Size(w_set) == 4
        api.PySet_Add(w_set, space.wrap(6))
        assert api.PySet_Size(w_set) == 5
        api.PySet_Discard(w_set, space.wrap(6))
        assert api.PySet_Size(w_set) == 4

    def test_set_contains(self, space, api):
        w_set = api.PySet_New(space.wrap([1,2,3,4]))
        assert api.PySet_Contains(w_set, space.wrap(1))
        assert not api.PySet_Contains(w_set, space.wrap(0))

    def test_set_pop_clear(self, space, api):
        w_set = api.PySet_New(space.wrap([1,2,3,4]))
        w_obj = api.PySet_Pop(w_set)
        assert space.int_w(w_obj) in (1,2,3,4)
        assert space.len_w(w_set) == 3
        api.PySet_Clear(w_set)
        assert space.len_w(w_set) == 0

    def test_anyset_checkexact(self, space, api):
        w_set = api.PySet_New(space.wrap([1, 2, 3, 4]))
        w_frozenset = space.newfrozenset([space.wrap(i) for i in [1, 2, 3, 4]])
        assert api.PyAnySet_CheckExact(w_set)
        assert api.PyAnySet_CheckExact(w_frozenset)

class AppTestSetObject(AppTestCpythonExtensionBase):
    def test_set_macro_cast(self):
        module = self.import_extension('foo', [
            ("test_macro_cast", "METH_NOARGS",
             """
             PyObject* o = PySet_New(NULL);
             // no PySetObject
             char* dumb_pointer = (char*) o;

             PySet_GET_SIZE(o);
             PySet_GET_SIZE(dumb_pointer);

             return o;
             """
            )
        ])
