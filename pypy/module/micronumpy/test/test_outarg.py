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
        from _numpypy import array, negative, zeros
        a = array([[1, 2], [3, 4]])
        c = zeros((2,2,2))
        b = negative(a + a, out=c[1])
        assert (b == [[-2, -4], [-6, -8]]).all()
        assert (c[:, :, 1] == [[0, 0], [-4, -8]]).all()

    def test_ufunc_cast(self):
        from _numpypy import array, negative
        cast_error = raises(TypeError, negative, array(16,dtype=float),
                                                 out=array(0, dtype=int))
        assert str(cast_error.value) == \
            "Cannot cast ufunc negative output from dtype('float64') to dtype('int64') with casting rule 'same_kind'"
        
