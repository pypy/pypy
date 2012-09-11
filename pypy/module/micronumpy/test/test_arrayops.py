
from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest

class AppTestNumSupport(BaseNumpyAppTest):
    def test_where(self):
        from _numpypy import where, ones, zeros, array
        a = [1, 2, 3, 0, -3]
        a = where(array(a) > 0, ones(5), zeros(5))
        assert (a == [1, 1, 1, 0, 0]).all()

    def test_where_differing_dtypes(self):
        from _numpypy import array, ones, zeros, where
        a = [1, 2, 3, 0, -3]
        a = where(array(a) > 0, ones(5, dtype=int), zeros(5, dtype=float))
        assert (a == [1, 1, 1, 0, 0]).all()

    def test_where_broadcast(self):
        from _numpypy import array, where
        a = where(array([[1, 2, 3], [4, 5, 6]]) > 3, [1, 1, 1], 2)
        assert (a == [[2, 2, 2], [1, 1, 1]]).all()
        a = where(True, [1, 1, 1], 2)
        assert (a == [1, 1, 1]).all()

    def test_where_errors(self):
        from _numpypy import where, array
        raises(ValueError, "where([1, 2, 3], [3, 4, 5])")
        raises(ValueError, "where([1, 2, 3], [3, 4, 5], [6, 7])")
        assert where(True, 1, 2) == array(1)
        assert where(False, 1, 2) == array(2)
        assert (where(True, [1, 2, 3], 2) == [1, 2, 3]).all()
        assert (where(False, 1, [1, 2, 3]) == [1, 2, 3]).all()
        assert (where([1, 2, 3], True, False) == [True, True, True]).all()

    #def test_where_1_arg(self):
    #    xxx

    def test_where_invalidates(self):
        from _numpypy import where, ones, zeros, array
        a = array([1, 2, 3, 0, -3])
        b = where(a > 0, ones(5), zeros(5))
        a[0] = 0
        assert (b == [1, 1, 1, 0, 0]).all()
