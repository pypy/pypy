import py

from pypy.module.cpyext.test.test_api import BaseApiTest

class TestTupleObject(BaseApiTest):
    def test_tupleobject(self, space, api):
        assert not api.PyTuple_Check(space.w_None)
        assert api.PyTuple_SetItem(space.w_None, 0, space.w_None) == -1
        atuple = space.newtuple([0, 1, 'yay'])
        assert api.PyTuple_Size(atuple) == 3
        assert api.PyTuple_GET_SIZE(atuple) == 3
        raises(TypeError, api.PyTuple_Size(space.newlist([])))
        api.PyErr_Clear()
