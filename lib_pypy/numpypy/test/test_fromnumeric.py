from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest


class AppTestFromNumeric(BaseNumpyAppTest):
    def test_argmax(self):
        # tests taken from numpy/core/fromnumeric.py docstring
        from numpypy import array, arange, argmax
        a = arange(6).reshape((2,3))
        assert argmax(a) == 5
        # assert (argmax(a, axis=0) == array([1, 1, 1])).all()
        # assert (argmax(a, axis=1) == array([2, 2])).all()
        b = arange(6)
        b[1] = 5
        assert argmax(b) == 1

    def test_argmin(self):
        # tests adapted from test_argmax
        from numpypy import array, arange, argmin
        a = arange(6).reshape((2,3))
        assert argmin(a) == 0
        # assert (argmax(a, axis=0) == array([0, 0, 0])).all()
        # assert (argmax(a, axis=1) == array([0, 0])).all()
        b = arange(6)
        b[1] = 0
        assert argmin(b) == 0

    def test_shape(self):
        # tests taken from numpy/core/fromnumeric.py docstring
        from numpypy import array, identity, shape
        assert shape(identity(3)) == (3, 3)
        assert shape([[1, 2]]) == (1, 2)
        assert shape([0]) ==  (1,)
        assert shape(0) == ()
        # a = array([(1, 2), (3, 4)], dtype=[('x', 'i4'), ('y', 'i4')])
        # assert shape(a) == (2,)

    def test_sum(self):
        # tests taken from numpy/core/fromnumeric.py docstring
        from numpypy import array, sum, ones
        assert sum([0.5, 1.5])== 2.0
        assert sum([[0, 1], [0, 5]]) == 6
        # assert sum([0.5, 0.7, 0.2, 1.5], dtype=int32) == 1
        # assert (sum([[0, 1], [0, 5]], axis=0) == array([0, 6])).all()
        # assert (sum([[0, 1], [0, 5]], axis=1) == array([1, 5])).all()
        # If the accumulator is too small, overflow occurs:
        # assert ones(128, dtype=int8).sum(dtype=int8) == -128

    def test_amin(self):
        # tests taken from numpy/core/fromnumeric.py docstring
        from numpypy import array, arange, amin
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

    def test_amax(self):
        # tests taken from numpy/core/fromnumeric.py docstring
        from numpypy import array, arange, amax
        a = arange(4).reshape((2,2))
        assert amax(a) == 3
        # assert (amax(a, axis=0) == array([2, 3])).all()
        # assert (amax(a, axis=1) == array([1, 3])).all()
        # # NaN behaviour
        # b = arange(5, dtype=float)
        # b[2] = NaN
        # assert amax(b) == nan
        # assert nanmax(b) == 4.0

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
        # assert (np.var(a,0) == array([ 1.,  1.])).all()
        # assert (np.var(a,1) == array([ 0.25,  0.25])).all()

    def test_std(self):
        from numpypy import array, std
        a = array([[1, 2], [3, 4]])
        assert std(a) ==  1.1180339887498949
        # assert (std(a, axis=0) == array([ 1.,  1.])).all()
        # assert (std(a, axis=1) == array([ 0.5,  0.5]).all()

    def test_mean(self):
        from numpypy import array, mean
        assert mean(array(range(5))) == 2.0
        assert mean(range(5)) == 2.0

    def test_reshape(self):
        from numpypy import arange, array, dtype, reshape
        a = arange(12)
        b = reshape(a, (3, 4))
        assert b.shape == (3, 4)
        a = range(12)
        b = reshape(a, (3, 4))
        assert b.shape == (3, 4)
        a = array(range(105)).reshape(3, 5, 7)
        assert reshape(a, 1, -1).shape == (1, 105)
        assert reshape(a, 1, 1, -1).shape == (1, 1, 105)
        assert reshape(a, -1, 1, 1).shape == (105, 1, 1)
