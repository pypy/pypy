from pypy.module.test_lib_pypy.numpypy.test_base import BaseNumpyAppTest

class AppTestShapeBase(BaseNumpyAppTest):
    def test_dstack(self):
        import numpypy as np
        a = np.array((1, 2, 3))
        b = np.array((2, 3, 4))
        c = np.dstack((a, b))
        assert np.array_equal(c, [[[1, 2], [2, 3], [3, 4]]])

        a = np.array([[1], [2], [3]])
        b = np.array([[2], [3], [4]])
        c = np.dstack((a, b))
        assert np.array_equal(c, [[[1, 2]], [[2, 3]], [[3, 4]]])

        #skip("https://bugs.pypy.org/issue1394")
        for shape1, shape2 in [[(4, 2, 3), (4, 2, 7)],
                               [(7, 2, 0), (7, 2, 10)],
                               [(7, 2, 0), (7, 2, 0)]]:
            a, b = np.ones(shape1), np.ones(shape2)
            assert np.all(np.dstack((a, b)) ==
                          np.ones((a.shape[0],
                                   a.shape[1],
                                   a.shape[2] + b.shape[2])))

        for shape1, shape2 in [[(4, 2, 3, 5), (4, 2, 7, 5)],
                               [(7, 2, 0, 5), (7, 2, 10, 5)],
                               [(7, 2, 0, 5), (7, 2, 0, 5)]]:
            a, b = np.ones(shape1), np.ones(shape2)
            assert np.all(np.dstack((a, b)) ==
                          np.ones((a.shape[0],
                                   a.shape[1],
                                   a.shape[2] + b.shape[2],
                                   a.shape[3])))
