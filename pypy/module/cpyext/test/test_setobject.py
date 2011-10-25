import py

from pypy.module.cpyext.pyobject import PyObject, PyObjectP, make_ref, from_ref
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.conftest import gettestobjspace


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
