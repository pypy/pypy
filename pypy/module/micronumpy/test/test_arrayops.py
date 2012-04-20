
from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest

class AppTestNumSupport(BaseNumpyAppTest):
    def test_where(self):
        from _numpypy import where, ones, zeros, array
        a = [1, 2, 3, 0, -3]
        a = where(array(a) > 0, ones(5), zeros(5))
        assert (a == [1, 1, 1, 0, 0]).all()

    def test_where_invalidates(self):
        from _numpypy import where, ones, zeros, array
        a = array([1, 2, 3, 0, -3])
        b = where(a > 0, ones(5), zeros(5))
        a[0] = 0
        assert (b == [1, 1, 1, 0, 0]).all()
