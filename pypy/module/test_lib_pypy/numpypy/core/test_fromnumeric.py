from pypy.module.test_lib_pypy.numpypy.test_base import BaseNumpyAppTest


class AppTestFromNumeric(BaseNumpyAppTest):
    def test_argmax(self):
        # tests taken from numpy/core/fromnumeric.py docstring
        from numpypy import arange, argmax
        a = arange(6).reshape((2,3))
        assert argmax(a) == 5
        # assert (argmax(a, axis=0) == array([1, 1, 1])).all()
        # assert (argmax(a, axis=1) == array([2, 2])).all()
        b = arange(6)
        b[1] = 5
        assert argmax(b) == 1

    def test_argmin(self):
        # tests adapted from test_argmax
        from numpypy import arange, argmin
        a = arange(6).reshape((2,3))
        assert argmin(a) == 0
        #assert (argmin(a, axis=0) == array([0, 0, 0])).all()
        #assert (argmin(a, axis=1) == array([0, 0])).all()
        b = arange(6)
        b[1] = 0
        assert argmin(b) == 0

    def test_ravel(self):
        import numpypy as np
        a = np.ravel(np.float64(1))
        assert np.array_equal(a, [1.])
        a = np.ravel(np.array([[1, 2, 3], [4, 5, 6]]))
        assert np.array_equal(a, [1, 2, 3, 4, 5, 6])

    def test_shape(self):
        # tests taken from numpy/core/fromnumeric.py docstring
        from numpypy import identity, shape
        assert shape(identity(3)) == (3, 3)
        assert shape([[1, 2]]) == (1, 2)
        assert shape([0]) ==  (1,)
        assert shape(0) == ()
        # a = array([(1, 2), (3, 4)], dtype=[('x', 'i4'), ('y', 'i4')])
        # assert shape(a) == (2,)

    def test_clip(self):
        import numpypy as np
        a = np.arange(10)
        b = np.clip(a, 1, 8)
        assert (b == [1, 1, 2, 3, 4, 5, 6, 7, 8, 8]).all()
        assert (a == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]).all()
        b = np.clip(a, 3, 6, out=a)
        assert (b == [3, 3, 3, 3, 4, 5, 6, 6, 6, 6]).all()
        assert (a == [3, 3, 3, 3, 4, 5, 6, 6, 6, 6]).all()
        a = np.arange(10)
        b = np.clip(a, [3,4,1,1,1,4,4,4,4,4], 8)
        assert (b == [3, 4, 2, 3, 4, 5, 6, 7, 8, 8]).all()
        assert (a == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]).all()

    def test_sum(self):
        # tests taken from numpy/core/fromnumeric.py docstring
        from numpypy import sum, ones, zeros, array
        assert sum([0.5, 1.5])== 2.0
        assert sum([[0, 1], [0, 5]]) == 6
        # assert sum([0.5, 0.7, 0.2, 1.5], dtype=int32) == 1
        assert (sum([[0, 1], [0, 5]], axis=0) == array([0, 6])).all()
        assert (sum([[0, 1], [0, 5]], axis=1) == array([1, 5])).all()
        # If the accumulator is too small, overflow occurs:
        # assert ones(128, dtype=int8).sum(dtype=int8) == -128

        assert sum(range(10)) == 45
        assert sum(array(range(10))) == 45
        assert list(sum(zeros((0, 2)), axis=1)) == []

        a = array([[1, 2], [3, 4]])
        out = array([[0, 0], [0, 0]])
        c = sum(a, axis=0, out=out[0])
        assert (c == [4, 6]).all()
        assert (c == out[0]).all()
        assert (c != out[1]).all()

    def test_amin(self):
        # tests taken from numpy/core/fromnumeric.py docstring
        from numpypy import array, arange, amin, zeros
        a = arange(4).reshape((2,2))
        assert amin(a) == 0
        # # Minima along the first axis
        # assert (amin(a, axis=0) == array([0, 1])).all()
        # # Minima along the second axis
        # assert (amin(a, axis=1) == array([0, 2])).all()
        # # NaN behaviour
        # b = arange(5, dtype=float)
        # b[2] = NaN
        # assert amin(b) == nan
        # assert nanmin(b) == 0.0

        assert amin(range(10)) == 0
        assert amin(array(range(10))) == 0
        assert list(amin(zeros((0, 2)), axis=1)) == []

        a = array([[1, 2], [3, 4]])
        out = array([[0, 0], [0, 0]])
        c = amin(a, axis=1, out=out[0])
        assert (c == [1, 3]).all()
        assert (c == out[0]).all()
        assert (c != out[1]).all()

    def test_amax(self):
        # tests taken from numpy/core/fromnumeric.py docstring
        from numpypy import array, arange, amax, zeros
        a = arange(4).reshape((2,2))
        assert amax(a) == 3
        # assert (amax(a, axis=0) == array([2, 3])).all()
        # assert (amax(a, axis=1) == array([1, 3])).all()
        # # NaN behaviour
        # b = arange(5, dtype=float)
        # b[2] = NaN
        # assert amax(b) == nan
        # assert nanmax(b) == 4.0

        assert amax(range(10)) == 9
        assert amax(array(range(10))) == 9
        assert list(amax(zeros((0, 2)), axis=1)) == []

        a = array([[1, 2], [3, 4]])
        out = array([[0, 0], [0, 0]])
        c = amax(a, axis=1, out=out[0])
        assert (c == [2, 4]).all()
        assert (c == out[0]).all()
        assert (c != out[1]).all()

    def test_alen(self):
        # tests taken from numpy/core/fromnumeric.py docstring
        from numpypy import array, zeros, alen
        a = zeros((7,4,5))
        assert a.shape[0] == 7
        assert alen(a)    == 7

    def test_ndim(self):
        # tests taken from numpy/core/fromnumeric.py docstring
        from numpypy import array, ndim
        assert ndim([[1,2,3],[4,5,6]]) == 2
        assert ndim(array([[1,2,3],[4,5,6]])) == 2
        assert ndim(1) == 0

    def test_rank(self):
        # tests taken from numpy/core/fromnumeric.py docstring
        from numpypy import array, rank
        assert rank([[1,2,3],[4,5,6]]) == 2
        assert rank(array([[1,2,3],[4,5,6]])) == 2
        assert rank(1) == 0

    def test_var(self):
        from numpypy import array, var
        a = array([[1,2],[3,4]])
        assert var(a) == 1.25
        assert (var(a,0) == array([ 1.,  1.])).all()
        assert (var(a,1) == array([ 0.25,  0.25])).all()

    def test_std(self):
        from numpypy import array, std
        a = array([[1, 2], [3, 4]])
        assert std(a) ==  1.1180339887498949
        assert (std(a, axis=0) == array([ 1.,  1.])).all()
        assert (std(a, axis=1) == array([ 0.5,  0.5])).all()

    def test_mean(self):
        from numpypy import array, mean, arange
        assert mean(array(range(5))) == 2.0
        assert mean(range(5)) == 2.0
        assert (mean(arange(10).reshape(5, 2), axis=0) == [4, 5]).all()
        assert (mean(arange(10).reshape(5, 2), axis=1) == [0.5, 2.5, 4.5, 6.5, 8.5]).all()

    def test_reshape(self):
        from numpypy import arange, array, dtype, reshape
        a = arange(12)
        b = reshape(a, (3, 4))
        assert b.shape == (3, 4)
        a = range(12)
        b = reshape(a, (3, 4))
        assert b.shape == (3, 4)
        a = array(range(105)).reshape(3, 5, 7)
        assert reshape(a, (1, -1)).shape == (1, 105)
        assert reshape(a, (1, 1, -1)).shape == (1, 1, 105)
        assert reshape(a, (-1, 1, 1)).shape == (105, 1, 1)

    def test_transpose(self):
        from numpypy import arange, array, transpose, ones
        x = arange(4).reshape((2,2))
        assert (transpose(x) == array([[0, 2],[1, 3]])).all()
        # Once axes argument is implemented, add more tests
        import sys
        if '__pypy__' in sys.builtin_module_names:
            raises(NotImplementedError, "transpose(x, axes=(1, 0, 2))")
        # x = ones((1, 2, 3))
        # assert transpose(x, (1, 0, 2)).shape == (2, 1, 3)

    def test_fromnumeric(self):
        from numpypy import array, swapaxes
        x = array([[1,2,3]])
        assert (swapaxes(x,0,1) == array([[1], [2], [3]])).all()
        x = array([[[0,1],[2,3]],[[4,5],[6,7]]])
        assert (swapaxes(x,0,2) == array([[[0, 4], [2, 6]],
                                          [[1, 5], [3, 7]]])).all()
