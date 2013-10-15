
from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest


class AppTestBaseRepr(BaseNumpyAppTest):
    def test_base3(self):
        from numpypy import base_repr
        assert base_repr(3**5, 3) == '100000'

    def test_positive(self):
        from numpypy import base_repr
        assert base_repr(12, 10) == '12'
        assert base_repr(12, 10, 4) == '000012'
        assert base_repr(12, 4) == '30'
        assert base_repr(3731624803700888, 36) == '10QR0ROFCEW'

    def test_negative(self):
        from numpypy import base_repr
        assert base_repr(-12, 10) == '-12'
        assert base_repr(-12, 10, 4) == '-000012'
        assert base_repr(-12, 4) == '-30'


class AppTestRepr(BaseNumpyAppTest):
    def test_repr(self):
        from numpypy import array
        assert repr(array([1, 2, 3, 4])) == 'array([1, 2, 3, 4])'

    def test_repr_2(self):
        from numpypy import array, zeros
        int_size = array(5).dtype.itemsize
        a = array(range(5), float)
        assert repr(a) == "array([ 0.,  1.,  2.,  3.,  4.])"
        a = array([], float)
        assert repr(a) == "array([], dtype=float64)"
        a = zeros(1001)
        assert repr(a) == "array([ 0.,  0.,  0., ...,  0.,  0.,  0.])"
        a = array(range(5), int)
        if a.dtype.itemsize == int_size:
            assert repr(a) == "array([0, 1, 2, 3, 4])"
        else:
            assert repr(a) == "array([0, 1, 2, 3, 4], dtype=int64)"
        a = array(range(5), 'int32')
        if a.dtype.itemsize == int_size:
            assert repr(a) == "array([0, 1, 2, 3, 4])"
        else:
            assert repr(a) == "array([0, 1, 2, 3, 4], dtype=int32)"
        a = array([], long)
        assert repr(a) == "array([], dtype=int64)"
        a = array([True, False, True, False], "?")
        assert repr(a) == "array([ True, False,  True, False], dtype=bool)"
        a = zeros([])
        assert repr(a) == "array(0.0)"
        a = array(0.2)
        assert repr(a) == "array(0.2)"
        a = array([2])
        assert repr(a) == "array([2])"

    def test_repr_multi(self):
        from numpypy import arange, zeros, array
        a = zeros((3, 4))
        assert repr(a) == '''array([[ 0.,  0.,  0.,  0.],
       [ 0.,  0.,  0.,  0.],
       [ 0.,  0.,  0.,  0.]])'''
        a = zeros((2, 3, 4))
        assert repr(a) == '''array([[[ 0.,  0.,  0.,  0.],
        [ 0.,  0.,  0.,  0.],
        [ 0.,  0.,  0.,  0.]],

       [[ 0.,  0.,  0.,  0.],
        [ 0.,  0.,  0.,  0.],
        [ 0.,  0.,  0.,  0.]]])'''
        a = arange(1002).reshape((2, 501))
        assert repr(a) == '''array([[   0,    1,    2, ...,  498,  499,  500],
       [ 501,  502,  503, ...,  999, 1000, 1001]])'''
        assert repr(a.T) == '''array([[   0,  501],
       [   1,  502],
       [   2,  503],
       ..., 
       [ 498,  999],
       [ 499, 1000],
       [ 500, 1001]])'''
        a = arange(2).reshape((2,1))
        assert repr(a) == '''array([[0],
       [1]])'''

    def test_repr_slice(self):
        from numpypy import array, zeros
        a = array(range(5), float)
        b = a[1::2]
        assert repr(b) == "array([ 1.,  3.])"
        a = zeros(2002)
        b = a[::2]
        assert repr(b) == "array([ 0.,  0.,  0., ...,  0.,  0.,  0.])"
        a = array((range(5), range(5, 10)), dtype="int16")
        b = a[1, 2:]
        assert repr(b) == "array([7, 8, 9], dtype=int16)"
        # an empty slice prints its shape
        b = a[2:1, ]
        assert repr(b) == "array([], shape=(0, 5), dtype=int16)"

    def test_str(self):
        from numpypy import array, zeros
        a = array(range(5), float)
        assert str(a) == "[ 0.  1.  2.  3.  4.]"
        assert str((2 * a)[:]) == "[ 0.  2.  4.  6.  8.]"
        a = zeros(1001)
        assert str(a) == "[ 0.  0.  0. ...,  0.  0.  0.]"

        a = array(range(5), dtype=long)
        assert str(a) == "[0 1 2 3 4]"
        a = array([True, False, True, False], dtype="?")
        assert str(a) == "[ True False  True False]"

        a = array(range(5), dtype="int8")
        assert str(a) == "[0 1 2 3 4]"

        a = array(range(5), dtype="int16")
        assert str(a) == "[0 1 2 3 4]"

        a = array((range(5), range(5, 10)), dtype="int16")
        assert str(a) == "[[0 1 2 3 4]\n [5 6 7 8 9]]"

        a = array(3, dtype=int)
        assert str(a) == "3"

        a = zeros((400, 400), dtype=int)
        assert str(a) == '[[0 0 0 ..., 0 0 0]\n [0 0 0 ..., 0 0 0]\n [0 0 0 ..., 0 0 0]\n ..., \n [0 0 0 ..., 0 0 0]\n [0 0 0 ..., 0 0 0]\n [0 0 0 ..., 0 0 0]]'
        a = zeros((2, 2, 2))
        r = str(a)
        assert r == '[[[ 0.  0.]\n  [ 0.  0.]]\n\n [[ 0.  0.]\n  [ 0.  0.]]]'

    def test_str_slice(self):
        from numpypy import array, zeros
        a = array(range(5), float)
        b = a[1::2]
        assert str(b) == "[ 1.  3.]"
        a = zeros(2002)
        b = a[::2]
        assert str(b) == "[ 0.  0.  0. ...,  0.  0.  0.]"
        a = array((range(5), range(5, 10)), dtype="int16")
        b = a[1, 2:]
        assert str(b) == "[7 8 9]"
        b = a[2:1, ]
        assert str(b) == "[]"

    def test_equal(self):
        from numpypy import array, array_equal

        a = [1, 2, 3]
        b = [1, 2, 3]

        assert array_equal(a, b)
        assert array_equal(a, array(b))
        assert array_equal(array(a), b)
        assert array_equal(array(a), array(b))

    def test_not_equal(self):
        from numpypy import array, array_equal

        a = [1, 2, 3]
        b = [1, 2, 4]

        assert not array_equal(a, b)
        assert not array_equal(a, array(b))
        assert not array_equal(array(a), b)
        assert not array_equal(array(a), array(b))

    def test_mismatched_shape(self):
        from numpypy import array, array_equal

        a = [1, 2, 3]
        b = [[1, 2, 3], [1, 2, 3]]

        assert not array_equal(a, b)
        assert not array_equal(a, array(b))
        assert not array_equal(array(a), b)
        assert not array_equal(array(a), array(b))

    def test_equiv(self):
        import numpypy as np

        assert np.array_equiv([1, 2], [1, 2])
        assert not np.array_equiv([1, 2], [1, 3])
        assert np.array_equiv([1, 2], [[1, 2], [1, 2]])
        assert not np.array_equiv([1, 2], [[1, 2, 1, 2], [1, 2, 1, 2]])
        assert not np.array_equiv([1, 2], [[1, 2], [1, 3]])


class AppTestNumeric(BaseNumpyAppTest):
    def test_outer(self):
        from numpypy import array, outer
        a = [1, 2, 3]
        b = [4, 5, 6]
        res = outer(a, b)
        expected = array([[ 4,  5,  6],
                          [ 8, 10, 12],
                          [12, 15, 18]])
        assert (res == expected).all()

    def test_vdot(self):
        import numpypy as np
        a = np.array([1+2j,3+4j])
        b = np.array([5+6j,7+8j])
        c = np.vdot(a, b)
        assert c == (70-8j)
        c = np.vdot(b, a)
        assert c == (70+8j)

        a = np.array([[1, 4], [5, 6]])
        b = np.array([[4, 1], [2, 2]])
        c = np.vdot(a, b)
        assert c == 30
        c = np.vdot(b, a)
        assert c == 30

    def test_identity(self):
        from numpypy import array, int32, float64, dtype, identity
        a = identity(0)
        assert len(a) == 0
        assert a.dtype == dtype('float64')
        assert a.shape == (0, 0)
        b = identity(1, dtype=int32)
        assert len(b) == 1
        assert b[0][0] == 1
        assert b.shape == (1, 1)
        assert b.dtype == dtype('int32')
        c = identity(2)
        assert c.shape == (2, 2)
        assert (c == [[1, 0], [0, 1]]).all()
        d = identity(3, dtype='int32')
        assert d.shape == (3, 3)
        assert d.dtype == dtype('int32')
        assert (d == [[1, 0, 0], [0, 1, 0], [0, 0, 1]]).all()
