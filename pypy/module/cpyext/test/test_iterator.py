from pypy.module.cpyext.test.test_api import BaseApiTest


class TestIterator(BaseApiTest):
    def test_check_iter(self, space, api):
        assert api.PyIter_Check(space.iter(space.wrap("a")))
        assert api.PyIter_Check(space.iter(space.newlist([])))
        assert not api.PyIter_Check(space.w_type)
        assert not api.PyIter_Check(space.wrap(2))

    def test_getIter(self, space, api):
        w_iter = api.PyObject_GetIter(space.wrap([1, 2, 3]))
        assert space.unwrap(api.PyIter_Next(w_iter)) == 1
        assert space.unwrap(api.PyIter_Next(w_iter)) == 2
        assert space.unwrap(api.PyIter_Next(w_iter)) == 3
        assert api.PyIter_Next(w_iter) is None
        assert not api.PyErr_Occurred()

    def test_iternext_error(self,space, api):
        assert api.PyIter_Next(space.w_None) is None
        assert api.PyErr_Occurred() is space.w_TypeError
        api.PyErr_Clear()
