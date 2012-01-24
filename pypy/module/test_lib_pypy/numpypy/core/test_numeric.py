
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
        a = array(range(5), long)
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
