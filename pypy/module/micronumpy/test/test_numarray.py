from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest
from pypy.module.micronumpy.interp_numarray import NDimArray
from pypy.module.micronumpy import signature
from pypy.conftest import gettestobjspace

class MockDtype(object):
    signature = signature.BaseSignature()
    def malloc(self, size):
        return None

class TestNumArrayDirect(object):
    def newslice(self, *args):
        return self.space.newslice(*[self.space.wrap(arg) for arg in args])

    def newtuple(self, *args):
        args_w = []
        for arg in args:
            if isinstance(arg, int):
                args_w.append(self.space.wrap(arg))
            else:
                args_w.append(arg)
        return self.space.newtuple(args_w)
    
    def test_shards(self):
        a = NDimArray(100, [10, 5, 3], MockDtype())
        assert a.shards == [15, 3, 1]
        assert a.backshards == [135, 12, 2]

    def test_create_slice(self):
        space = self.space
        a = NDimArray(10*5*3, [10, 5, 3], MockDtype())
        s = a.create_slice(space, space.wrap(3))
        assert s.start == 45
        assert s.shards == [3, 1]
        assert s.backshards == [12, 2]
        s = a.create_slice(space, self.newslice(1, 9, 2))
        assert s.start == 15
        assert s.shards == [30, 3, 1]
        assert s.backshards == [90, 12, 2]
        s = a.create_slice(space, space.newtuple([
            self.newslice(1, 5, 3), self.newslice(1, 2, 1), space.wrap(1)]))
        assert s.start == 19
        assert s.shape == [2, 1]
        assert s.shards == [45, 3]
        assert s.backshards == [45, 3]
        s = a.create_slice(space, self.newtuple(
            self.newslice(None, None, None), space.wrap(2)))
        assert s.start == 6
        assert s.shape == [10, 3]

    def test_slice_of_slice(self):
        space = self.space
        a = NDimArray(10*5*3, [10, 5, 3], MockDtype())
        s = a.create_slice(space, space.wrap(5))
        assert s.start == 15*5
        s2 = s.create_slice(space, space.wrap(3))
        assert s2.shape == [3]
        assert s2.shards == [1]
        assert s2.parent is a
        assert s2.backshards == [2]
        assert s2.start == 5*15 + 3*3
        s = a.create_slice(space, self.newslice(1, 5, 3))
        s2 = s.create_slice(space, space.newtuple([
            self.newslice(None, None, None), space.wrap(2)]))
        assert s2.shape == [2, 3]
        assert s2.shards == [45, 1]
        assert s2.backshards == [90, 2]
        assert s2.start == 1*15 + 2*3

    def test_negative_step(self):
        space = self.space
        a = NDimArray(10*5*3, [10, 5, 3], MockDtype())
        s = a.create_slice(space, self.newslice(None, None, -2))
        assert s.start == 135
        assert s.shards == [-30, 3, 1]
        assert s.backshards == [-150, 12, 2]

    def test_index_of_single_item(self):
        a = NDimArray(10*5*3, [10, 5, 3], MockDtype())
        r = a._index_of_single_item(self.space, self.newtuple(1, 2, 2))
        assert r == 1 * 3 * 5 + 2 * 3 + 2
        s = a.create_slice(self.space, self.newtuple(
            self.newslice(None, None, None), 2))
        r = s._index_of_single_item(self.space, self.newtuple(1, 0))
        assert r == a._index_of_single_item(self.space, self.newtuple(1, 2, 0))
        r = s._index_of_single_item(self.space, self.newtuple(1, 1))
        assert r == a._index_of_single_item(self.space, self.newtuple(1, 2, 1))

class AppTestNumArray(BaseNumpyAppTest):
    def test_type(self):
        from numpy import array
        ar = array(range(5))
        assert type(ar) is type(ar + ar)

    def test_init(self):
        from numpy import zeros
        a = zeros(15)
        # Check that storage was actually zero'd.
        assert a[10] == 0.0
        # And check that changes stick.
        a[13] = 5.3
        assert a[13] == 5.3

    def test_empty(self):
        """
        Test that empty() works.
        """

        from numpy import empty
        a = empty(2)
        a[1] = 1.0
        assert a[1] == 1.0

    def test_ones(self):
        from numpy import ones
        a = ones(3)
        assert len(a) == 3
        assert a[0] == 1
        raises(IndexError, "a[3]")
        a[2] = 4
        assert a[2] == 4

    def test_copy(self):
        from numpy import array
        a = array(range(5))
        b = a.copy()
        for i in xrange(5):
            assert b[i] == a[i]
        a[3] = 22
        assert b[3] == 3

    def test_iterator_init(self):
        from numpy import array
        a = array(range(5))
        assert a[3] == 3
        a = array(1)
        assert a[0] == 1
        assert a.shape == ()

    def test_getitem(self):
        from numpy import array
        a = array(range(5))
        raises(IndexError, "a[5]")
        a = a + a
        raises(IndexError, "a[5]")
        assert a[-1] == 8
        raises(IndexError, "a[-6]")

    def test_getitem_tuple(self):
        from numpy import array
        a = array(range(5))
        raises(IndexError, "a[(1,2)]")
        for i in xrange(5):
            assert a[(i,)] == i
        b = a[()]
        for i in xrange(5):
            assert a[i] == b[i]

    def test_setitem(self):
        from numpy import array
        a = array(range(5))
        a[-1] = 5.0
        assert a[4] == 5.0
        raises(IndexError, "a[5] = 0.0")
        raises(IndexError, "a[-6] = 3.0")

    def test_setitem_tuple(self):
        from numpy import array
        a = array(range(5))
        raises(IndexError, "a[(1,2)] = [0,1]")
        for i in xrange(5):
            a[(i,)] = i+1
            assert a[i] == i+1
        a[()] = range(5)
        for i in xrange(5):
            assert a[i] == i

    def test_setslice_array(self):
        from numpy import array
        a = array(range(5))
        b = array(range(2))
        a[1:4:2] = b
        assert a[1] == 0.
        assert a[3] == 1.
        b[::-1] = b
        assert b[0] == 1.
        assert b[1] == 0.

    def test_setslice_of_slice_array(self):
        from numpy import array, zeros
        a = zeros(5)
        a[::2] = array([9., 10., 11.])
        assert a[0] == 9.
        assert a[2] == 10.
        assert a[4] == 11.
        a[1:4:2][::-1] = array([1., 2.])
        assert a[0] == 9.
        assert a[1] == 2.
        assert a[2] == 10.
        assert a[3] == 1.
        assert a[4] == 11.
        a = zeros(10)
        a[::2][::-1][::2] = array(range(1,4))
        assert a[8] == 1.
        assert a[4] == 2.
        assert a[0] == 3.

    def test_setslice_list(self):
        from numpy import array
        a = array(range(5), float)
        b = [0., 1.]
        a[1:4:2] = b
        assert a[1] == 0.
        assert a[3] == 1.

    def test_setslice_constant(self):
        from numpy import array
        a = array(range(5), float)
        a[1:4:2] = 0.
        assert a[1] == 0.
        assert a[3] == 0.
    
    def test_scalar(self):
        from numpy import array
        a = array(3)
        assert a[0] == 3 

    def test_len(self):
        from numpy import array
        a = array(range(5))
        assert len(a) == 5
        assert len(a + a) == 5

    def test_shape(self):
        from numpy import array
        a = array(range(5))
        assert a.shape == (5,)
        b = a + a
        assert b.shape == (5,)
        c = a[:3]
        assert c.shape == (3,)

    def test_add(self):
        from numpy import array
        a = array(range(5))
        b = a + a
        for i in range(5):
            assert b[i] == i + i

        a = array([True, False, True, False], dtype="?")
        b = array([True, True, False, False], dtype="?")
        c = a + b
        for i in range(4):
            assert c[i] == bool(a[i] + b[i])

    def test_add_other(self):
        from numpy import array
        a = array(range(5))
        b = array([i for i in reversed(range(5))])
        c = a + b
        for i in range(5):
            assert c[i] == 4

    def test_add_constant(self):
        from numpy import array
        a = array(range(5))
        b = a + 5
        for i in range(5):
            assert b[i] == i + 5

    def test_radd(self):
        from numpy import array
        r = 3 + array(range(3))
        for i in range(3):
            assert r[i] == i + 3

    def test_add_list(self):
        from numpy import array
        a = array(range(5))
        b = list(reversed(range(5)))
        c = a + b
        assert isinstance(c, array)
        for i in range(5):
            assert c[i] == 4

    def test_subtract(self):
        from numpy import array
        a = array(range(5))
        b = a - a
        for i in range(5):
            assert b[i] == 0

    def test_subtract_other(self):
        from numpy import array
        a = array(range(5))
        b = array([1, 1, 1, 1, 1])
        c = a - b
        for i in range(5):
            assert c[i] == i - 1

    def test_subtract_constant(self):
        from numpy import array
        a = array(range(5))
        b = a - 5
        for i in range(5):
            assert b[i] == i - 5

    def test_mul(self):
        from numpy import array, dtype
        a = array(range(5))
        b = a * a
        for i in range(5):
            assert b[i] == i * i

        a = array(range(5), dtype=bool)
        b = a * a
        assert b.dtype is dtype(bool)
        assert b[0] is False
        for i in range(1, 5):
            assert b[i] is True

    def test_mul_constant(self):
        from numpy import array
        a = array(range(5))
        b = a * 5
        for i in range(5):
            assert b[i] == i * 5

    def test_div(self):
        from math import isnan
        from numpy import array, dtype, inf

        a = array(range(1, 6))
        b = a / a
        for i in range(5):
            assert b[i] == 1

        a = array(range(1, 6), dtype=bool)
        b = a / a
        assert b.dtype is dtype("int8")
        for i in range(5):
            assert b[i] == 1

        a = array([-1, 0, 1])
        b = array([0, 0, 0])
        c = a / b
        assert (c == [0, 0, 0]).all()

        a = array([-1.0, 0.0, 1.0])
        b = array([0.0, 0.0, 0.0])
        c = a / b
        assert c[0] == -inf
        assert isnan(c[1])
        assert c[2] == inf

        b = array([-0.0, -0.0, -0.0])
        c = a / b
        assert c[0] == inf
        assert isnan(c[1])
        assert c[2] == -inf

    def test_div_other(self):
        from numpy import array
        a = array(range(5))
        b = array([2, 2, 2, 2, 2], float)
        c = a / b
        for i in range(5):
            assert c[i] == i / 2.0

    def test_div_constant(self):
        from numpy import array
        a = array(range(5))
        b = a / 5.0
        for i in range(5):
            assert b[i] == i / 5.0

    def test_pow(self):
        from numpy import array
        a = array(range(5), float)
        b = a ** a
        for i in range(5):
            print b[i], i**i
            assert b[i] == i**i

    def test_pow_other(self):
        from numpy import array
        a = array(range(5), float)
        b = array([2, 2, 2, 2, 2])
        c = a ** b
        for i in range(5):
            assert c[i] == i ** 2

    def test_pow_constant(self):
        from numpy import array
        a = array(range(5), float)
        b = a ** 2
        for i in range(5):
            assert b[i] == i ** 2

    def test_mod(self):
        from numpy import array
        a = array(range(1,6))
        b = a % a
        for i in range(5):
            assert b[i] == 0

        a = array(range(1, 6), float)
        b = (a + 1) % a
        assert b[0] == 0
        for i in range(1, 5):
            assert b[i] == 1

    def test_mod_other(self):
        from numpy import array
        a = array(range(5))
        b = array([2, 2, 2, 2, 2])
        c = a % b
        for i in range(5):
            assert c[i] == i % 2

    def test_mod_constant(self):
        from numpy import array
        a = array(range(5))
        b = a % 2
        for i in range(5):
            assert b[i] == i % 2

    def test_pos(self):
        from numpy import array
        a = array([1.,-2.,3.,-4.,-5.])
        b = +a
        for i in range(5):
            assert b[i] == a[i]

        a = +array(range(5))
        for i in range(5):
            assert a[i] == i

    def test_neg(self):
        from numpy import array
        a = array([1.,-2.,3.,-4.,-5.])
        b = -a
        for i in range(5):
            assert b[i] == -a[i]

        a = -array(range(5), dtype="int8")
        for i in range(5):
            assert a[i] == -i

    def test_abs(self):
        from numpy import array
        a = array([1.,-2.,3.,-4.,-5.])
        b = abs(a)
        for i in range(5):
            assert b[i] == abs(a[i])

        a = abs(array(range(-5, 5), dtype="int8"))
        for i in range(-5, 5):
            assert a[i + 5] == abs(i)

    def test_auto_force(self):
        from numpy import array
        a = array(range(5))
        b = a - 1
        a[2] = 3
        for i in range(5):
            assert b[i] == i - 1

        a = array(range(5))
        b = a + a
        c = b + b
        b[1] = 5
        assert c[1] == 4

    def test_getslice(self):
        from numpy import array
        a = array(range(5))
        s = a[1:5]
        assert len(s) == 4
        for i in range(4):
            assert s[i] == a[i+1]

        s = (a + a)[1:2]
        assert len(s) == 1
        assert s[0] == 2
        s[:1] = array([5])
        assert s[0] == 5

    def test_getslice_step(self):
        from numpy import array
        a = array(range(10))
        s = a[1:9:2]
        assert len(s) == 4
        for i in range(4):
            assert s[i] == a[2*i+1]

    def test_slice_update(self):
        from numpy import array
        a = array(range(5))
        s = a[0:3]
        s[1] = 10
        assert a[1] == 10
        a[2] = 20
        assert s[2] == 20


    def test_slice_invaidate(self):
        # check that slice shares invalidation list with
        from numpy import array
        a = array(range(5))
        s = a[0:2]
        b = array([10,11])
        c = s + b
        a[0] = 100
        assert c[0] == 10
        assert c[1] == 12
        d = s + b
        a[1] = 101
        assert d[0] == 110
        assert d[1] == 12

    def test_mean(self):
        from numpy import array
        a = array(range(5))
        assert a.mean() == 2.0
        assert a[:4].mean() == 1.5

    def test_sum(self):
        from numpy import array
        a = array(range(5))
        assert a.sum() == 10.0
        assert a[:4].sum() == 6.0

        a = array([True] * 5, bool)
        assert a.sum() == 5

    def test_prod(self):
        from numpy import array
        a = array(range(1,6))
        assert a.prod() == 120.0
        assert a[:4].prod() == 24.0

    def test_max(self):
        from numpy import array
        a = array([-1.2, 3.4, 5.7, -3.0, 2.7])
        assert a.max() == 5.7
        b = array([])
        raises(ValueError, "b.max()")

    def test_max_add(self):
        from numpy import array
        a = array([-1.2, 3.4, 5.7, -3.0, 2.7])
        assert (a+a).max() == 11.4

    def test_min(self):
        from numpy import array
        a = array([-1.2, 3.4, 5.7, -3.0, 2.7])
        assert a.min() == -3.0
        b = array([])
        raises(ValueError, "b.min()")

    def test_argmax(self):
        import sys
        from numpy import array
        a = array([-1.2, 3.4, 5.7, -3.0, 2.7])
        r = a.argmax()
        assert r == 2
        b = array([])
        try:
            b.argmax()
        except:
            pass
        else:
            raise Exception("Did not raise")

        a = array(range(-5, 5))
        r = a.argmax()
        assert r == 9
        b = a[::2]
        r = b.argmax()
        assert r == 4
        r = (a + a).argmax()
        assert r == 9

    def test_argmin(self):
        from numpy import array
        a = array([-1.2, 3.4, 5.7, -3.0, 2.7])
        assert a.argmin() == 3
        b = array([])
        raises(ValueError, "b.argmin()")

    def test_all(self):
        from numpy import array
        a = array(range(5))
        assert a.all() == False
        a[0] = 3.0
        assert a.all() == True
        b = array([])
        assert b.all() == True

    def test_any(self):
        from numpy import array, zeros
        a = array(range(5))
        assert a.any() == True
        b = zeros(5)
        assert b.any() == False
        c = array([])
        assert c.any() == False

    def test_dot(self):
        from numpy import array
        a = array(range(5))
        assert a.dot(a) == 30.0

        a = array(range(5))
        assert a.dot(range(5)) == 30

    def test_dot_constant(self):
        from numpy import array
        a = array(range(5))
        b = a.dot(2.5)
        for i in xrange(5):
            assert b[i] == 2.5 * a[i]

    def test_dtype_guessing(self):
        from numpy import array, dtype

        assert array([True]).dtype is dtype(bool)
        assert array([True, False]).dtype is dtype(bool)
        assert array([True, 1]).dtype is dtype(int)
        assert array([1, 2, 3]).dtype is dtype(int)
        assert array([1L, 2, 3]).dtype is dtype(long)
        assert array([1.2, True]).dtype is dtype(float)
        assert array([1.2, 5]).dtype is dtype(float)
        assert array([]).dtype is dtype(float)

    def test_comparison(self):
        import operator
        from numpy import array, dtype

        a = array(range(5))
        b = array(range(5), float)
        for func in [
            operator.eq, operator.ne, operator.lt, operator.le, operator.gt,
            operator.ge
        ]:
            c = func(a, 3)
            assert c.dtype is dtype(bool)
            for i in xrange(5):
                assert c[i] == func(a[i], 3)

            c = func(b, 3)
            assert c.dtype is dtype(bool)
            for i in xrange(5):
                assert c[i] == func(b[i], 3)

    def test_nonzero(self):
        from numpy import array
        a = array([1, 2])
        raises(ValueError, bool, a)
        raises(ValueError, bool, a == a)
        assert bool(array(1))
        assert not bool(array(0))
        assert bool(array([1]))
        assert not bool(array([0]))

class AppTestMultiDim(BaseNumpyAppTest):
    def test_init(self):
        import numpy
        a = numpy.zeros((2, 2))
        assert len(a) == 2

    def test_shape(self):
        import numpy
        assert numpy.zeros(1).shape == (1,)
        assert numpy.zeros((2, 2)).shape == (2,2)
        assert numpy.zeros((3, 1, 2)).shape == (3, 1, 2)
        assert len(numpy.zeros((3, 1, 2))) == 3
        raises(TypeError, len, numpy.zeros(()))

    def test_getsetitem(self):
        import numpy
        a = numpy.zeros((2, 3, 1))
        raises(IndexError, a.__getitem__, (2, 0, 0))
        raises(IndexError, a.__getitem__, (0, 3, 0))
        raises(IndexError, a.__getitem__, (0, 0, 1))
        assert a[1, 1, 0] == 0
        a[1, 2, 0] = 3
        assert a[1, 2, 0] == 3
        assert a[1, 1, 0] == 0

    def test_slices(self):
        import numpy
        a = numpy.zeros((4, 3, 2))
        raises(IndexError, a.__getitem__, (4,))
        raises(IndexError, a.__getitem__, (3, 3))
        raises(IndexError, a.__getitem__, (slice(None), 3))
        a[0,1,1] = 13
        a[1,2,1] = 15
        b = a[0]
        assert len(b) == 3
        assert b.shape == (3, 2)
        assert b[1,1] == 13
        b = a[1]
        assert b.shape == (3, 2)
        assert b[2,1] == 15
        b = a[:,1]
        assert b.shape == (4, 2)
        assert b[0,1] == 13
        b = a[:,1,:]
        assert b.shape == (4, 2)
        assert b[0,1] == 13
        b = a[1, 2]
        assert b[1] == 15
        b = a[:]
        assert b.shape == (4, 3, 2)
        assert b[1,2,1] == 15
        assert b[0,1,1] == 13
        b = a[:][:,1][:]
        assert b[2,1] == 0.0
        assert b[0,1] == 13
        raises(IndexError, b.__getitem__, (4, 1))
        assert a[0][1][1] == 13
        assert a[1][2][1] == 15

    def test_init_2(self):
        import numpy
        raises(ValueError, numpy.array, [[1], 2])
        raises(ValueError, numpy.array, [[1, 2], [3]])
        raises(ValueError, numpy.array, [[[1, 2], [3, 4], 5]])
        raises(ValueError, numpy.array, [[[1, 2], [3, 4], [5]]])
        a = numpy.array([[1, 2], [4, 5]])
        assert a[0, 1] == 2
        assert a[0][1] == 2
        a = numpy.array(([[[1, 2], [3, 4], [5, 6]]]))
        assert (a[0, 1] == [3, 4]).all()

    def test_setitem_slice(self):
        import numpy
        a = numpy.zeros((3, 4))
        a[1] = [1, 2, 3, 4]
        assert a[1, 2] == 3
        raises(TypeError, a[1].__setitem__, [1, 2, 3])
        a = numpy.array([[1, 2], [3, 4]])
        assert (a == [[1, 2], [3, 4]]).all()
        a[1] = numpy.array([5, 6])
        assert (a == [[1, 2], [5, 6]]).all()
        a[:,1] = numpy.array([8, 10])
        assert (a == [[1, 8], [5, 10]]).all()
        a[0,::-1] = numpy.array([11, 12])
        assert (a == [[12, 11], [5, 10]]).all()

    def test_ufunc(self):
        from numpy import array
        a = array([[1, 2], [3, 4], [5, 6]])
        assert ((a + a) == array([[1+1, 2+2], [3+3, 4+4], [5+5, 6+6]])).all()

    def test_getitem_add(self):
        from numpy import array
        a = array([[1, 2], [3, 4], [5, 6], [7, 8], [9, 10]])
        assert (a + a)[1, 1] == 8

    def test_ufunc_negative(self):
        from numpy import array, negative
        a = array([[1, 2], [3, 4]])
        b = negative(a + a)
        assert (b == [[-2, -4], [-6, -8]]).all()

    def test_getitem_3(self):
        from numpy import array
        a = array([[1, 2], [3, 4], [5, 6], [7, 8], [9, 10], [11, 12], [13, 14]])
        b = a[::2]
        assert (b == [[1, 2], [5, 6], [9, 10], [13, 14]]).all()
        c = b + b
        assert c[1][1] == 12

    def test_broadcast(self):
        skip("not working")
        import numpy
        a = numpy.zeros((100, 100))
        b = numpy.ones(100)
        a[:,:] = b
        assert a[13,15] == 1

class AppTestSupport(object):
    def setup_class(cls):
        import struct
        cls.space = gettestobjspace(usemodules=('micronumpy',))
        cls.w_data = cls.space.wrap(struct.pack('dddd', 1, 2, 3, 4))

    def test_fromstring(self):
        from numpy import fromstring
        a = fromstring(self.data)
        for i in range(4):
            assert a[i] == i + 1
        raises(ValueError, fromstring, "abc")

class AppTestRepr(BaseNumpyAppTest):
    def test_repr(self):
        from numpy import array, zeros
        a = array(range(5), float)
        assert repr(a) == "array([0.0, 1.0, 2.0, 3.0, 4.0])"
        a = array([], float)
        assert repr(a) == "array([], dtype=float64)"
        a = zeros(1001)
        assert repr(a) == "array([0.0, 0.0, 0.0, ..., 0.0, 0.0, 0.0])"
        a = array(range(5), long)
        assert repr(a) == "array([0, 1, 2, 3, 4])"
        a = array([], long)
        assert repr(a) == "array([], dtype=int64)"
        a = array([True, False, True, False], "?")
        assert repr(a) == "array([True, False, True, False], dtype=bool)"

    def test_repr_multi(self):
        from numpy import array, zeros
        a = zeros((3,4))
        assert repr(a) == '''array([[0.0, 0.0, 0.0, 0.0],
       [0.0, 0.0, 0.0, 0.0],
       [0.0, 0.0, 0.0, 0.0]])'''
        a = zeros((2,3,4))
        assert repr(a) == '''array([[[0.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0]],

       [[0.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0]]])'''

    def test_repr_slice(self):
        from numpy import array, zeros
        a = array(range(5), float)
        b = a[1::2]
        assert repr(b) == "array([1.0, 3.0])"
        a = zeros(2002)
        b = a[::2]
        assert repr(b) == "array([0.0, 0.0, 0.0, ..., 0.0, 0.0, 0.0])"
        a = array((range(5),range(5,10)), dtype="int16")
        b=a[1,2:]
        assert repr(b) == "array([7, 8, 9], dtype=int16)"
        #This is the way cpython numpy does it - an empty slice prints its shape
        b=a[2:1,]
        assert repr(b) == "array([], shape=(0, 5), dtype=int16)"

    def test_str(self):
        from numpy import array, zeros
        a = array(range(5), float)
        assert str(a) == "[0.0 1.0 2.0 3.0 4.0]"
        assert str((2*a)[:]) == "[0.0 2.0 4.0 6.0 8.0]"
        a = zeros(1001)
        assert str(a) == "[0.0 0.0 0.0 ..., 0.0 0.0 0.0]"

        a = array(range(5), dtype=long)
        assert str(a) == "[0 1 2 3 4]"
        a = array([True, False, True, False], dtype="?")
        assert str(a) == "[True False True False]"

        a = array(range(5), dtype="int8")
        assert str(a) == "[0 1 2 3 4]"

        a = array(range(5), dtype="int16")
        assert str(a) == "[0 1 2 3 4]"

        a = array((range(5),range(5,10)), dtype="int16")
        assert str(a) == "[[0 1 2 3 4],\n [5 6 7 8 9]]"

        a = array(3,dtype=int)
        assert str(a) == "3"

    def test_str_slice(self):
        from numpy import array, zeros
        a = array(range(5), float)
        b = a[1::2]
        assert str(b) == "[1.0 3.0]"
        a = zeros(2002)
        b = a[::2]
        assert str(b) == "[0.0 0.0 0.0 ..., 0.0 0.0 0.0]"
        a = array((range(5),range(5,10)), dtype="int16")
        b=a[1,2:]
        assert str(b) == "[7 8 9]"
        b=a[2:1,]
        assert str(b) == "[]"
