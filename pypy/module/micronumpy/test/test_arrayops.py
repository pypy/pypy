
from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest

class AppTestNumSupport(BaseNumpyAppTest):
    def test_where(self):
        from _numpypy import where, ones, zeros, array
        a = [1, 2, 3, 0, -3]
        a = where(array(a) > 0, ones(5), zeros(5))
        assert (a == [1, 1, 1, 0, 0]).all()
