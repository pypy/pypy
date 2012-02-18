import py
from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest

class AppTestOutArg(BaseNumpyAppTest):
    def test_reduce_out(self):
        from numpypy import arange, zeros, array
        a = arange(15).reshape(5, 3)
        b = arange(12).reshape(4,3)
        c = a.sum(0, out=b[1])
        assert (c == [30, 35, 40]).all()
        assert (c == b[1]).all()
        raises(ValueError, 'a.prod(0, out=arange(10))')
        a=arange(12).reshape(3,2,2)
        raises(ValueError, 'a.sum(0, out=arange(12).reshape(3,2,2))')
        raises(ValueError, 'a.sum(0, out=arange(3))')
        c = array([-1, 0, 1]).sum(out=zeros([], dtype=bool))
        #You could argue that this should product False, but
        # that would require an itermediate result. Cpython numpy
        # gives True.
        assert c == True
        a = array([[-1, 0, 1], [1, 0, -1]])
        c = a.sum(0, out=zeros((3,), dtype=bool))
        assert (c == [True, False, True]).all()
        c = a.sum(1, out=zeros((2,), dtype=bool))
        assert (c == [True, True]).all()

    def test_reduce_intermediary(self):
        from numpypy import arange, array
        a = arange(15).reshape(5, 3)
        b = array(range(3), dtype=bool)
        c = a.prod(0, out=b)
        assert(b == [False,  True,  True]).all()

    def test_ufunc_out(self):
        from _numpypy import array, negative, zeros, sin
        from math import sin as msin
        a = array([[1, 2], [3, 4]])
        c = zeros((2,2,2))
        b = negative(a + a, out=c[1])
        #test for view, and also test that forcing out also forces b
        assert (c[:, :, 1] == [[0, 0], [-4, -8]]).all()
        assert (b == [[-2, -4], [-6, -8]]).all()
        #Test broadcast, type promotion
        b = negative(3, out=a)
        assert (a == -3).all()
        c = zeros((2, 2), dtype=float)
        b = negative(3, out=c)
        assert b.dtype.kind == c.dtype.kind
        assert b.shape == c.shape
        a = array([1, 2])
        b = sin(a, out=c)
        assert(c == [[msin(1), msin(2)]] * 2).all()
        b = sin(a, out=c+c)
        assert (c == b).all()

        #Test shape agreement
        a = zeros((3,4))
        b = zeros((3,5))
        raises(ValueError, 'negative(a, out=b)')
        b = zeros((1,4))
        raises(ValueError, 'negative(a, out=b)')

    def test_ufunc_cast(self):
        from _numpypy import array, negative
        cast_error = raises(TypeError, negative, array(16,dtype=float),
                                                 out=array(0, dtype=int))
        assert str(cast_error.value) == \
            "Cannot cast ufunc negative output from dtype('float64') to dtype('int64') with casting rule 'same_kind'"
        
