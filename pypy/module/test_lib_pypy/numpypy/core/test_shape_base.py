from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest

class AppTestShapeBase(BaseNumpyAppTest):

    def test_atleast_1d(self):
        from numpypy import array, array_equal
        import numpypy as np
        a = np.atleast_1d(1.0)
        assert np.array_equal(a, [ 1.])
        
        x = np.arange(9.0).reshape(3,3)
        a = np.atleast_1d(x)
        assert np.array_equal(a, [[ 0.,  1.,  2.],
                                  [ 3.,  4.,  5.],
                                  [ 6.,  7.,  8.]])
        assert np.atleast_1d(x) is x

        a = np.atleast_1d(1, [3, 4])
        assert len(a) == 2
        assert array_equal(a[0], [1])
        assert array_equal(a[1], [3, 4])

    def test_atleast_2d(self):
        import numpypy as np
        a = np.atleast_2d(3.0)
        assert np.array_equal(a, [[ 3.]])

        x = np.arange(3.0)
        a = np.atleast_2d(x)
        assert np.array_equal(a, [[ 0.,  1.,  2.]])

        a = np.atleast_2d(1, [1, 2], [[1, 2]])
        assert len(a) == 3
        assert np.array_equal(a[0], [[1]])
        assert np.array_equal(a[1], [[1, 2]])
        assert np.array_equal(a[2], [[1, 2]])

    def test_atleast_3d(self):
        import numpypy as np

        a = np.atleast_3d(3.0)
        assert np.array_equal(a, [[[ 3.]]])

        x = np.arange(3.0)
        assert np.atleast_3d(x).shape == (1, 3, 1)

        x = np.arange(12.0).reshape(4,3)
        assert np.atleast_3d(x).shape == (4, 3, 1)

        a = np.atleast_3d([1, 2])
        assert np.array_equal(a, [[[1],
                                   [2]]])
        assert a.shape == (1, 2, 1)

        a = np.atleast_3d([[1, 2]])
        assert np.array_equal(a, [[[1],
                                   [2]]])
        assert a.shape == (1, 2, 1)

        a = np.atleast_3d([[[1, 2]]])
        assert np.array_equal(a, [[[1, 2]]])
        assert a.shape == (1, 1, 2)

    def test_vstack(self):
        import numpypy as np

        a = np.array([1, 2, 3])
        b = np.array([2, 3, 4])
        c = np.vstack((a,b))
        assert np.array_equal(c, [[1, 2, 3],
                                  [2, 3, 4]])

        a = np.array([[1], [2], [3]])
        b = np.array([[2], [3], [4]])
        c = np.vstack((a,b))
        assert np.array_equal(c, [[1],
                                  [2],
                                  [3],
                                  [2],
                                  [3],
                                  [4]])

    def test_hstack(self):
        import numpypy as np
        a = np.array((1,2,3))
        b = np.array((2,3,4))
        c = np.hstack((a,b))
        assert np.array_equal(c, [1, 2, 3, 2, 3, 4])
        
        a = np.array([[1],[2],[3]])
        b = np.array([[2],[3],[4]])
        c = np.hstack((a,b))
        assert np.array_equal(c, [[1, 2],
                                  [2, 3],
                                  [3, 4]])

    def test_dstack(self):
        import numpypy as np
        a = np.array((1,2,3))
        b = np.array((2,3,4))
        c = np.dstack((a,b))
        assert np.array_equal(c, [[[1, 2], [2, 3], [3, 4]]])

        a = np.array([[1],[2],[3]])
        b = np.array([[2],[3],[4]])
        c = np.dstack((a,b))
        assert np.array_equal(c, [[[1, 2]], [[2, 3]], [[3, 4]]])
