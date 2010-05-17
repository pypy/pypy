from pypy.module.cpyext.test.test_api import BaseApiTest


class TestIterator(BaseApiTest):
    def test_check_iter(self, space, api):
        assert api.PyIter_Check(space.wrap(iter("a")))
        assert api.PyIter_Check(space.wrap(iter([])))
        assert not api.PyIter_Check(space.wrap(type))
        assert not api.PyIter_Check(space.wrap(2))
