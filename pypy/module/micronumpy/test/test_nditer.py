import py
from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest


class AppTestNDIter(BaseNumpyAppTest):
    def test_basic(self):
        from numpy import arange, nditer
        a = arange(6).reshape(2,3)
        r = []
        for x in nditer(a):
            r.append(x)
        assert r == [0, 1, 2, 3, 4, 5]
        r = []

        for x in nditer(a.T):
            r.append(x)
        assert r == [0, 1, 2, 3, 4, 5]

    def test_order(self):
        from numpy import arange, nditer
        a = arange(6).reshape(2,3)
        r = []
        for x in nditer(a, order='C'):
            r.append(x)
        assert r == [0, 1, 2, 3, 4, 5]
        r = []
        for x in nditer(a, order='F'):
            r.append(x)
        assert r == [0, 3, 1, 4, 2, 5]

    def test_readwrite(self):
        from numpy import arange, nditer
        a = arange(6).reshape(2,3)
        for x in nditer(a, op_flags=['readwrite']):
            x[...] = 2 * x
        assert (a == [[0, 2, 4], [6, 8, 10]]).all()

    def test_external_loop(self):
        from numpy import arange, nditer, array
        a = arange(24).reshape(2, 3, 4)
        r = []
        n = 0
        for x in nditer(a, flags=['external_loop']):
            r.append(x)
            n += 1
        assert n == 1
        assert (array(r) == range(24)).all()
        r = []
        n = 0
        for x in nditer(a, flags=['external_loop'], order='F'):
            r.append(x)
            n += 1
        assert n == 12
        assert (array(r) == [[ 0, 12], [ 4, 16], [ 8, 20], [ 1, 13], [ 5, 17], [ 9, 21], [ 2, 14], [ 6, 18], [10, 22], [ 3, 15], [ 7, 19], [11, 23]]).all()
        e = None
        try:
            r[0][0] = 0
        except ValueError, ex:
            e = ex
        assert e

    def test_index(self):
        from numpy import arange, nditer
        a = arange(6).reshape(2,3)

        r = []
        it = nditer(a, flags=['c_index'])
        assert it.has_index
        for value in it:
            r.append((value, it.index))
        assert r == [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5)]
        exc = None
        try:
            it.index
        except ValueError, e:
            exc = e
        assert exc

        r = []
        it = nditer(a, flags=['f_index'])
        assert it.has_index
        for value in it:
            r.append((value, it.index))
        assert r == [(0, 0), (1, 2), (2, 4), (3, 1), (4, 3), (5, 5)]

    @py.test.mark.xfail(reason="Fortran order not implemented")
    def test_iters_with_different_order(self):
        from numpy import nditer, array

        a = array([[1, 2], [3, 4]], order="C")
        b = array([[1, 2], [3, 4]], order="F")

        it = nditer([a, b])

        assert list(it) == zip(range(1, 5), range(1, 5))

    def test_interface(self):
        from numpy import arange, nditer, zeros
        import sys
        a = arange(6).reshape(2,3)
        r = []
        it = nditer(a, flags=['f_index'])
        while not it.finished:
            r.append((it[0], it.index))
            it.iternext()
        assert r == [(0, 0), (1, 2), (2, 4), (3, 1), (4, 3), (5, 5)]
        it = nditer(a, flags=['multi_index'], op_flags=['writeonly'])
        if '__pypy__' in sys.builtin_module_names:
            raises(NotImplementedError, 'it[0] = 3')
            skip('nditer.__setitem__ not implmented')
        while not it.finished:
            it[0] = it.multi_index[1] - it.multi_index[0]
            it.iternext()
        assert (a == [[0, 1, 2], [-1, 0, 1]]).all()
        b = zeros((2, 3))
        exc = raises(ValueError, nditer, b, flags=['c_index', 'external_loop'])
        assert str(exc.value).startswith("Iterator flag EXTERNAL_LOOP cannot")

    def test_buffered(self):
        from numpy import arange, nditer, array
        import sys
        a = arange(6).reshape(2,3)
        r = []
        if '__pypy__' in sys.builtin_module_names:
            raises(NotImplementedError, "nditer(a, flags=['external_loop', 'buffered'], order='F')")
            skip('nditer buffered flag not implmented')
        for x in nditer(a, flags=['external_loop', 'buffered'], order='F'):
            r.append(x)
        array_r = array(r)
        assert len(array_r.shape) == 2
        assert array_r.shape == (1, 6)
        assert (array_r == [0, 3, 1, 4, 2, 5]).all()

    def test_op_dtype(self):
        from numpy import arange, nditer, sqrt, array
        import sys
        a = arange(6).reshape(2,3) - 3
        if '__pypy__' in sys.builtin_module_names:
            raises(NotImplementedError, nditer, a, op_dtypes=['complex'])
            skip('nditer op_dtypes kwarg not implemented yet')
        exc = raises(ValueError, nditer, a, op_dtypes=['complex'])
        assert str(exc.value).startswith("Iterator operand required copying or buffering")
        r = []
        for x in nditer(a, op_flags=['readonly','copy'],
                        op_dtypes=['complex128']):
            r.append(sqrt(x))
        assert abs((array(r) - [1.73205080757j, 1.41421356237j, 1j, 0j,
                1+0j, 1.41421356237+0j]).sum()) < 1e-5
        r = []
        for x in nditer(a, flags=['buffered'],
                        op_dtypes=['complex128']):
            r.append(sqrt(x))
        assert abs((array(r) - [1.73205080757j, 1.41421356237j, 1j, 0j,
                            1+0j, 1.41421356237+0j]).sum()) < 1e-5

    def test_casting(self):
        from numpy import arange, nditer
        import sys
        a = arange(6.)
        if '__pypy__' in sys.builtin_module_names:
            raises(NotImplementedError, nditer, a, flags=['buffered'], op_dtypes=['float32'])
            skip('nditer casting not implemented yet')
        exc = raises(ValueError, nditer, a, flags=['buffered'], op_dtypes=['float32'])
        assert str(exc.value).startswith("Iterator operand 0 dtype could not be cast")
        r = []
        for x in nditer(a, flags=['buffered'], op_dtypes=['float32'],
                                casting='same_kind'):
            r.append(x)
        assert r == [0., 1., 2., 3., 4., 5.]
        exc = raises(ValueError, nditer, a, flags=['buffered'],
                        op_dtypes=['int32'], casting='same_kind')
        assert str(exc.value).startswith("Iterator operand 0 dtype could not be cast")
        r = []
        b = arange(6)
        exc = raises(ValueError, nditer, b, flags=['buffered'], op_dtypes=['float64'],
                                op_flags=['readwrite'], casting='same_kind')
        assert str(exc.value).startswith("Iterator requested dtype could not be cast")

    def test_broadcast(self):
        from numpy import arange, nditer
        a = arange(3)
        b = arange(6).reshape(2,3)
        r = []
        for x,y in nditer([a, b]):
            r.append((x, y))
        assert r == [(0, 0), (1, 1), (2, 2), (0, 3), (1, 4), (2, 5)]
        a = arange(2)
        exc = raises(ValueError, nditer, [a, b])
        assert str(exc.value).find('shapes (2) (2,3)') > 0

    def test_outarg(self):
        from numpy import nditer, zeros, arange

        def square1(a):
            it = nditer([a, None])
            for x,y in it:
                y[...] = x*x
            return it.operands[1]
        assert (square1([1, 2, 3]) == [1, 4, 9]).all()

        def square2(a, out=None):
            it = nditer([a, out], flags=['external_loop', 'buffered'],
                        op_flags=[['readonly'],
                                  ['writeonly', 'allocate', 'no_broadcast']])
            for x,y in it:
                y[...] = x*x
            return it.operands[1]
        assert (square2([1, 2, 3]) == [1, 4, 9]).all()
        b = zeros((3, ))
        c = square2([1, 2, 3], out=b)
        assert (c == [1., 4., 9.]).all()
        assert (b == c).all()
        exc = raises(ValueError, square2, arange(6).reshape(2, 3), out=b)
        assert str(exc.value).startswith('non-broadcastable output')

    def test_outer_product(self):
        from numpy import nditer, arange
        a = arange(3)
        b = arange(8).reshape(2,4)
        it = nditer([a, b, None], flags=['external_loop'],
                    op_axes=[[0, -1, -1], [-1, 0, 1], None])
        for x, y, z in it:
            z[...] = x*y
        assert it.operands[2].shape == (3, 2, 4)
        for i in range(a.size):
            assert (it.operands[2][i] == a[i]*b).all()

    def test_reduction(self):
        from numpy import nditer, arange, array
        import sys
        a = arange(24).reshape(2, 3, 4)
        b = array(0)
        if '__pypy__' in sys.builtin_module_names:
            raises(NotImplementedError, nditer, [a, b], flags=['reduce_ok'])
            skip('nditer reduce_ok not implemented yet')
        #reduction operands must be readwrite
        for x, y in nditer([a, b], flags=['reduce_ok', 'external_loop'],
                            op_flags=[['readonly'], ['readwrite']]):
            y[...] += x
        assert b == 276
        assert b == a.sum()

        # reduction and allocation requires op_axes and initialization
        it = nditer([a, None], flags=['reduce_ok', 'external_loop'],
                    op_flags=[['readonly'], ['readwrite', 'allocate']],
                    op_axes=[None, [0,1,-1]])
        it.operands[1][...] = 0
        for x, y in it:
            y[...] += x

        assert (it.operands[1] == [[6, 22, 38], [54, 70, 86]]).all()
        assert (it.operands[1] == a.sum(axis=2)).all()

        # previous example with buffering, requires more flags and reset
        it = nditer([a, None], flags=['reduce_ok', 'external_loop',
                                      'buffered', 'delay_bufalloc'],
                    op_flags=[['readonly'], ['readwrite', 'allocate']],
                    op_axes=[None, [0,1,-1]])
        it.operands[1][...] = 0
        it.reset()
        for x, y in it:
            y[...] += x

        assert (it.operands[1] == [[6, 22, 38], [54, 70, 86]]).all()
        assert (it.operands[1] == a.sum(axis=2)).all()

    def test_get_dtypes(self):
        from numpy import array, dtype, nditer
        x = array([1, 2])
        y = array([1.0, 2.0])
        assert nditer([x, y]).dtypes == (dtype("int64"), dtype("float64"))

    def test_multi_index(self):
        import numpy as np
        a = np.arange(6).reshape(2, 3)
        it = np.nditer(a, flags=['multi_index'])
        res = []
        while not it.finished:
            res.append((it[0], it.multi_index))
            it.iternext()
        assert res == [(0, (0, 0)), (1, (0, 1)),
                       (2, (0, 2)), (3, (1, 0)),
                       (4, (1, 1)), (5, (1, 2))]
