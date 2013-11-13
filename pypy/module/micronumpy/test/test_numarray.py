import py
import sys

from pypy.conftest import option
from pypy.module.micronumpy.appbridge import get_appbridge_cache
from pypy.module.micronumpy.iter import Chunk, Chunks
from pypy.module.micronumpy.interp_numarray import W_NDimArray
from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest


class MockDtype(object):
    class itemtype(object):
        @staticmethod
        def malloc(size):
            return None

        @staticmethod
        def get_element_size():
            return 1

    def __init__(self):
        self.base = self

    def get_size(self):
        return 1

def create_slice(space, a, chunks):
    return Chunks(chunks).apply(space, W_NDimArray(a)).implementation


def create_array(*args, **kwargs):
    return W_NDimArray.from_shape(*args, **kwargs).implementation


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

    def test_strides_f(self):
        a = create_array(self.space, [10, 5, 3], MockDtype(), order='F')
        assert a.strides == [1, 10, 50]
        assert a.backstrides == [9, 40, 100]

    def test_strides_c(self):
        a = create_array(self.space, [10, 5, 3], MockDtype(), order='C')
        assert a.strides == [15, 3, 1]
        assert a.backstrides == [135, 12, 2]
        a = create_array(self.space, [1, 0, 7], MockDtype(), order='C')
        assert a.strides == [7, 7, 1]
        assert a.backstrides == [0, 0, 6]

    def test_create_slice_f(self):
        a = create_array(self.space, [10, 5, 3], MockDtype(), order='F')
        s = create_slice(self.space, a, [Chunk(3, 0, 0, 1)])
        assert s.start == 3
        assert s.strides == [10, 50]
        assert s.backstrides == [40, 100]
        s = create_slice(self.space, a, [Chunk(1, 9, 2, 4)])
        assert s.start == 1
        assert s.strides == [2, 10, 50]
        assert s.backstrides == [6, 40, 100]
        s = create_slice(self.space, a, [Chunk(1, 5, 3, 2), Chunk(1, 2, 1, 1), Chunk(1, 0, 0, 1)])
        assert s.shape == [2, 1]
        assert s.strides == [3, 10]
        assert s.backstrides == [3, 0]
        s = create_slice(self.space, a, [Chunk(0, 10, 1, 10), Chunk(2, 0, 0, 1)])
        assert s.start == 20
        assert s.shape == [10, 3]

    def test_create_slice_c(self):
        a = create_array(self.space, [10, 5, 3], MockDtype(), order='C')
        s = create_slice(self.space, a, [Chunk(3, 0, 0, 1)])
        assert s.start == 45
        assert s.strides == [3, 1]
        assert s.backstrides == [12, 2]
        s = create_slice(self.space, a, [Chunk(1, 9, 2, 4)])
        assert s.start == 15
        assert s.strides == [30, 3, 1]
        assert s.backstrides == [90, 12, 2]
        s = create_slice(self.space, a, [Chunk(1, 5, 3, 2), Chunk(1, 2, 1, 1),
                            Chunk(1, 0, 0, 1)])
        assert s.start == 19
        assert s.shape == [2, 1]
        assert s.strides == [45, 3]
        assert s.backstrides == [45, 0]
        s = create_slice(self.space, a, [Chunk(0, 10, 1, 10), Chunk(2, 0, 0, 1)])
        assert s.start == 6
        assert s.shape == [10, 3]

    def test_slice_of_slice_f(self):
        a = create_array(self.space, [10, 5, 3], MockDtype(), order='F')
        s = create_slice(self.space, a, [Chunk(5, 0, 0, 1)])
        assert s.start == 5
        s2 = create_slice(self.space, s, [Chunk(3, 0, 0, 1)])
        assert s2.shape == [3]
        assert s2.strides == [50]
        assert s2.parent is a
        assert s2.backstrides == [100]
        assert s2.start == 35
        s = create_slice(self.space, a, [Chunk(1, 5, 3, 2)])
        s2 = create_slice(self.space, s, [Chunk(0, 2, 1, 2), Chunk(2, 0, 0, 1)])
        assert s2.shape == [2, 3]
        assert s2.strides == [3, 50]
        assert s2.backstrides == [3, 100]
        assert s2.start == 1 * 15 + 2 * 3

    def test_slice_of_slice_c(self):
        a = create_array(self.space, [10, 5, 3], MockDtype(), order='C')
        s = create_slice(self.space, a, [Chunk(5, 0, 0, 1)])
        assert s.start == 15 * 5
        s2 = create_slice(self.space, s, [Chunk(3, 0, 0, 1)])
        assert s2.shape == [3]
        assert s2.strides == [1]
        assert s2.parent is a
        assert s2.backstrides == [2]
        assert s2.start == 5 * 15 + 3 * 3
        s = create_slice(self.space, a, [Chunk(1, 5, 3, 2)])
        s2 = create_slice(self.space, s, [Chunk(0, 2, 1, 2), Chunk(2, 0, 0, 1)])
        assert s2.shape == [2, 3]
        assert s2.strides == [45, 1]
        assert s2.backstrides == [45, 2]
        assert s2.start == 1 * 15 + 2 * 3

    def test_negative_step_f(self):
        a = create_array(self.space, [10, 5, 3], MockDtype(), order='F')
        s = create_slice(self.space, a, [Chunk(9, -1, -2, 5)])
        assert s.start == 9
        assert s.strides == [-2, 10, 50]
        assert s.backstrides == [-8, 40, 100]

    def test_negative_step_c(self):
        a = create_array(self.space, [10, 5, 3], MockDtype(), order='C')
        s = create_slice(self.space, a, [Chunk(9, -1, -2, 5)])
        assert s.start == 135
        assert s.strides == [-30, 3, 1]
        assert s.backstrides == [-120, 12, 2]

    def test_shape_agreement(self):
        from pypy.module.micronumpy.strides import _shape_agreement
        assert _shape_agreement([3], [3]) == [3]
        assert _shape_agreement([1, 2, 3], [1, 2, 3]) == [1, 2, 3]
        _shape_agreement([2], [3]) == 0
        assert _shape_agreement([4, 4], []) == [4, 4]
        assert _shape_agreement([8, 1, 6, 1], [7, 1, 5]) == [8, 7, 6, 5]
        assert _shape_agreement([5, 2], [4, 3, 5, 2]) == [4, 3, 5, 2]

    def test_calc_new_strides(self):
        from pypy.module.micronumpy.strides import calc_new_strides
        assert calc_new_strides([2, 4], [4, 2], [4, 2], "C") == [8, 2]
        assert calc_new_strides([2, 4, 3], [8, 3], [1, 16], 'F') == [1, 2, 16]
        assert calc_new_strides([2, 3, 4], [8, 3], [1, 16], 'F') is None
        assert calc_new_strides([24], [2, 4, 3], [48, 6, 1], 'C') is None
        assert calc_new_strides([24], [2, 4, 3], [24, 6, 2], 'C') == [2]
        assert calc_new_strides([105, 1], [3, 5, 7], [35, 7, 1],'C') == [1, 1]
        assert calc_new_strides([1, 105], [3, 5, 7], [35, 7, 1],'C') == [105, 1]
        assert calc_new_strides([1, 105], [3, 5, 7], [35, 7, 1],'F') is None
        assert calc_new_strides([1, 1, 1, 105, 1], [15, 7], [7, 1],'C') == \
                                    [105, 105, 105, 1, 1]
        assert calc_new_strides([1, 1, 105, 1, 1], [7, 15], [1, 7],'F') == \
                                    [1, 1, 1, 105, 105]

    def test_to_coords(self):
        from pypy.module.micronumpy.strides import to_coords

        def _to_coords(index, order):
            return to_coords(self.space, [2, 3, 4], 24, order,
                             self.space.wrap(index))[0]

        assert _to_coords(0, 'C') == [0, 0, 0]
        assert _to_coords(1, 'C') == [0, 0, 1]
        assert _to_coords(-1, 'C') == [1, 2, 3]
        assert _to_coords(5, 'C') == [0, 1, 1]
        assert _to_coords(13, 'C') == [1, 0, 1]
        assert _to_coords(0, 'F') == [0, 0, 0]
        assert _to_coords(1, 'F') == [1, 0, 0]
        assert _to_coords(-1, 'F') == [1, 2, 3]
        assert _to_coords(5, 'F') == [1, 2, 0]
        assert _to_coords(13, 'F') == [1, 0, 2]

    def test_find_shape(self):
        from pypy.module.micronumpy.strides import find_shape_and_elems

        space = self.space
        shape, elems = find_shape_and_elems(space,
                                            space.newlist([space.wrap("a"),
                                                           space.wrap("b")]),
                                            None)
        assert shape == [2]
        assert space.str_w(elems[0]) == "a"
        assert space.str_w(elems[1]) == "b"

    def test_from_shape_and_storage(self):
        from rpython.rlib.rawstorage import alloc_raw_storage, raw_storage_setitem
        from rpython.rtyper.lltypesystem import rffi
        from pypy.module.micronumpy.interp_dtype import get_dtype_cache
        storage = alloc_raw_storage(4, track_allocation=False, zero=True)
        for i in range(4):
            raw_storage_setitem(storage, i, rffi.cast(rffi.UCHAR, i))
        #
        dtypes = get_dtype_cache(self.space)
        w_array = W_NDimArray.from_shape_and_storage(self.space, [2, 2],
                                                storage, dtypes.w_int8dtype)
        def get(i, j):
            return w_array.getitem(self.space, [i, j]).value
        assert get(0, 0) == 0
        assert get(0, 1) == 1
        assert get(1, 0) == 2
        assert get(1, 1) == 3

class AppTestNumArray(BaseNumpyAppTest):
    spaceconfig = dict(usemodules=["micronumpy", "struct", "binascii"])
    def w_CustomIndexObject(self, index):
        class CustomIndexObject(object):
            def __init__(self, index):
                self.index = index
            def __index__(self):
                return self.index

        return CustomIndexObject(index)

    def w_CustomIndexIntObject(self, index, value):
        class CustomIndexIntObject(object):
            def __init__(self, index, value):
                self.index = index
                self.value = value
            def __index__(self):
                return self.index
            def __int__(self):
                return self.value

        return CustomIndexIntObject(index, value)

    def w_CustomIntObject(self, value):
        class CustomIntObject(object):
            def __init__(self, value):
                self.value = value
            def __index__(self):
                return self.value

        return CustomIntObject(value)

    def test_ndarray(self):
        from numpy import ndarray, array, dtype, flatiter

        assert type(ndarray) is type
        assert repr(ndarray) == "<type 'numpy.ndarray'>"
        assert repr(flatiter) == "<type 'numpy.flatiter'>"
        assert type(array) is not type
        a = ndarray((2, 3))
        assert a.shape == (2, 3)
        assert a.dtype == dtype(float)

        raises(TypeError, ndarray, [[1], [2], [3]])

        a = ndarray(3, dtype=int)
        assert a.shape == (3,)
        assert a.dtype is dtype(int)
        a = ndarray([], dtype=float)
        assert a.shape == ()
        # test uninitialized value crash?
        assert len(str(a)) > 0

    def test_ndmin(self):
        from numpypy import array

        arr = array([[[1]]], ndmin=1)
        assert arr.shape == (1, 1, 1)

    def test_noop_ndmin(self):
        from numpypy import array

        arr = array([1], ndmin=3)
        assert arr.shape == (1, 1, 1)

    def test_array_copy(self):
        from numpypy import array
        a = array(range(12)).reshape(3,4)
        b = array(a, ndmin=4)
        assert b.shape == (1, 1, 3, 4)
        b = array(a, copy=False)
        b[0, 0] = 100
        assert a[0, 0] == 100
        b = array(a, copy=True, ndmin=2)
        b[0, 0] = 0
        assert a[0, 0] == 100
        b = array(a, dtype=float)
        assert (b[0] == [100, 1, 2, 3]).all()
        assert b.dtype.kind == 'f'
        b = array(a, copy=False, ndmin=4)
        b[0,0,0,0] = 0
        assert a[0, 0] == 0
        a = array([[[]]])
        # Simulate tiling an empty array, really tests repeat, reshape
        # b = tile(a, (3, 2, 5))
        reps = (3, 4, 5)
        c = array(a, copy=False, subok=True, ndmin=len(reps))
        d = c.reshape(3, 4, 0)
        e = d.repeat(3, 0)
        assert e.shape == (9, 4, 0)

    def test_type(self):
        from numpypy import array
        ar = array(range(5))
        assert type(ar) is type(ar + ar)

    def test_ndim(self):
        from numpypy import array
        x = array(0.2)
        assert x.ndim == 0
        x = array([1, 2])
        assert x.ndim == 1
        x = array([[1, 2], [3, 4]])
        assert x.ndim == 2
        x = array([[[1, 2], [3, 4]], [[5, 6], [7, 8]]])
        assert x.ndim == 3
        # numpy actually raises an AttributeError, but numpypy raises an
        # TypeError
        raises((TypeError, AttributeError), 'x.ndim = 3')

    def test_init(self):
        from numpypy import zeros
        a = zeros(15)
        # Check that storage was actually zero'd.
        assert a[10] == 0.0
        # And check that changes stick.
        a[13] = 5.3
        assert a[13] == 5.3
        assert zeros(()).shape == ()

    def test_size(self):
        from numpypy import array,arange,cos
        assert array(3).size == 1
        a = array([1, 2, 3])
        assert a.size == 3
        assert (a + a).size == 3
        ten = cos(1 + arange(10)).size
        assert ten == 10

    def test_empty(self):
        """
        Test that empty() works.
        """

        from numpypy import empty
        a = empty(2)
        a[1] = 1.0
        assert a[1] == 1.0

    def test_ones(self):
        from numpypy import ones, dtype
        a = ones(3)
        assert len(a) == 3
        assert a[0] == 1
        raises(IndexError, "a[3]")
        a[2] = 4
        assert a[2] == 4
        b = ones(3, complex)
        assert b[0] == 1+0j
        assert b.dtype is dtype(complex)

    def test_arange(self):
        from numpypy import arange, dtype
        a = arange(3)
        assert (a == [0, 1, 2]).all()
        assert a.dtype is dtype(int)
        a = arange(3.0)
        assert (a == [0., 1., 2.]).all()
        assert a.dtype is dtype(float)
        a = arange(3, 7)
        assert (a == [3, 4, 5, 6]).all()
        assert a.dtype is dtype(int)
        a = arange(3, 7, 2)
        assert (a == [3, 5]).all()
        a = arange(3, dtype=float)
        assert (a == [0., 1., 2.]).all()
        assert a.dtype is dtype(float)
        a = arange(0, 0.8, 0.1)
        assert len(a) == 8
        assert arange(False, True, True).dtype is dtype(int)

    def test_copy(self):
        from numpypy import arange, array
        a = arange(5)
        b = a.copy()
        for i in xrange(5):
            assert b[i] == a[i]
        a[3] = 22
        assert b[3] == 3

        a = array(1)
        assert a.copy() == a

        a = arange(8)
        b = a[::2]
        c = b.copy()
        assert (c == b).all()
        assert ((a + a).copy() == (a + a)).all()

        a = arange(15).reshape(5,3)
        b = a.copy()
        assert (b == a).all()

        a = array(['abc', 'def','xyz'], dtype='S3')
        b = a.copy()
        assert b[0] == a[0]

        a = arange(8)
        b = a.copy(order=None)
        assert (b == a).all()
        b = a.copy(order=0)
        assert (b == a).all()
        b = a.copy(order='C')
        assert (b == a).all()
        b = a.copy(order='K')
        assert (b == a).all()
        b = a.copy(order='A')
        assert (b == a).all()
        import sys
        if '__pypy__' in sys.builtin_module_names:
            raises(NotImplementedError, a.copy, order='F')
            raises(NotImplementedError, a.copy, order=True)

    def test_iterator_init(self):
        from numpypy import array
        a = array(range(5))
        assert a[3] == 3

    def test_getitem(self):
        from numpypy import array
        a = array(range(5))
        raises(IndexError, "a[5]")
        a = a + a
        raises(IndexError, "a[5]")
        assert a[-1] == 8
        raises(IndexError, "a[-6]")

    def test_getitem_float(self):
        from numpypy import array
        a = array([1, 2, 3, 4])
        assert a[1.2] == 2
        assert a[1.6] == 2
        assert a[-1.2] == 4

    def test_getitem_tuple(self):
        from numpypy import array
        a = array(range(5))
        raises(IndexError, "a[(1,2)]")
        for i in xrange(5):
            assert a[(i,)] == i
        b = a[()]
        for i in xrange(5):
            assert a[i] == b[i]

    def test_getitem_nd(self):
        from numpypy import arange
        a = arange(15).reshape(3, 5)
        assert a[1, 3] == 8
        assert a.T[1, 2] == 11

    def test_getitem_obj_index(self):
        from numpypy import arange
        a = arange(10)
        assert a[self.CustomIndexObject(1)] == 1

    def test_getitem_obj_prefer_index_to_int(self):
        from numpypy import arange
        a = arange(10)
        assert a[self.CustomIndexIntObject(0, 1)] == 0

    def test_getitem_obj_int(self):
        from numpypy import arange
        a = arange(10)
        assert a[self.CustomIntObject(1)] == 1

    def test_setitem(self):
        from numpypy import array
        a = array(range(5))
        a[-1] = 5.0
        assert a[4] == 5.0
        raises(IndexError, "a[5] = 0.0")
        raises(IndexError, "a[-6] = 3.0")
        a[1] = array(100)
        a[2] = array([100])
        assert a[1] == 100
        assert a[2] == 100
        a = array(range(5), dtype=float)
        a[0] = 0.005
        assert a[0] == 0.005
        a[1] = array(-0.005)
        a[2] = array([-0.005])
        assert a[1] == -0.005
        assert a[2] == -0.005

    def test_setitem_tuple(self):
        from numpypy import array
        a = array(range(5))
        raises(IndexError, "a[(1,2)] = [0,1]")
        for i in xrange(5):
            a[(i,)] = i + 1
            assert a[i] == i + 1
        a[()] = range(5)
        for i in xrange(5):
            assert a[i] == i

    def test_setitem_array(self):
        import numpy as np
        a = np.array((-1., 0, 1))/0.
        b = np.array([False, False, True], dtype=bool)
        a[b] = 100
        assert a[2] == 100

    def test_setitem_obj_index(self):
        from numpypy import arange
        a = arange(10)
        a[self.CustomIndexObject(1)] = 100
        assert a[1] == 100

    def test_setitem_obj_prefer_index_to_int(self):
        from numpypy import arange
        a = arange(10)
        a[self.CustomIndexIntObject(0, 1)] = 100
        assert a[0] == 100

    def test_setitem_obj_int(self):
        from numpypy import arange
        a = arange(10)
        a[self.CustomIntObject(1)] = 100
        assert a[1] == 100

    def test_delitem(self):
        import numpypy as np
        a = np.arange(10)
        exc = raises(ValueError, 'del a[2]')
        assert exc.value.message == 'cannot delete array elements'

    def test_access_swallow_exception(self):
        class ErrorIndex(object):
            def __index__(self):
                return 1 / 0

        class ErrorInt(object):
            def __int__(self):
                return 1 / 0

        # numpy will swallow errors in __int__ and __index__ and
        # just raise IndexError.

        from numpypy import arange
        a = arange(10)
        exc = raises(IndexError, "a[ErrorIndex()] == 0")
        assert exc.value.message == 'cannot convert index to integer'
        exc = raises(IndexError, "a[ErrorInt()] == 0")
        assert exc.value.message == 'cannot convert index to integer'

    def test_setslice_array(self):
        from numpypy import array
        a = array(range(5))
        b = array(range(2))
        a[1:4:2] = b
        assert a[1] == 0.
        assert a[3] == 1.
        b[::-1] = b
        assert b[0] == 1.
        assert b[1] == 0.

    def test_setslice_of_slice_array(self):
        from numpypy import array, zeros
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
        a[::2][::-1][::2] = array(range(1, 4))
        assert a[8] == 1.
        assert a[4] == 2.
        assert a[0] == 3.

    def test_setslice_list(self):
        from numpypy import array
        a = array(range(5), float)
        b = [0., 1.]
        a[1:4:2] = b
        assert a[1] == 0.
        assert a[3] == 1.

    def test_setslice_constant(self):
        from numpypy import array
        a = array(range(5), float)
        a[1:4:2] = 0.
        assert a[1] == 0.
        assert a[3] == 0.

    def test_newaxis(self):
        import math
        from numpypy import array, cos, zeros, newaxis
        a = array(range(5))
        b = array([range(5)])
        assert (a[newaxis] == b).all()
        a = array(range(3))
        b = array([1, 3])
        expected = zeros((3, 2))
        for x in range(3):
            for y in range(2):
                expected[x, y] = math.cos(a[x]) * math.cos(b[y])
        assert ((cos(a)[:,newaxis] * cos(b).T) == expected).all()

    def test_newaxis_slice(self):
        from numpypy import array, newaxis

        a = array(range(5))
        b = array(range(1,5))
        c = array([range(1,5)])
        d = array([[x] for x in range(1,5)])

        assert (a[1:] == b).all()
        assert (a[1:,newaxis] == d).all()
        assert (a[newaxis,1:] == c).all()

    def test_newaxis_assign(self):
        from numpypy import array, newaxis

        a = array(range(5))
        a[newaxis,1] = [2]
        assert a[1] == 2

    def test_newaxis_virtual(self):
        from numpypy import array, newaxis

        a = array(range(5))
        b = (a + a)[newaxis]
        c = array([[0, 2, 4, 6, 8]])
        assert (b == c).all()

    def test_newaxis_then_slice(self):
        from numpypy import array, newaxis
        a = array(range(5))
        b = a[newaxis]
        assert b.shape == (1, 5)
        assert (b[0,1:] == a[1:]).all()

    def test_slice_then_newaxis(self):
        from numpypy import array, newaxis
        a = array(range(5))
        b = a[2:]
        assert (b[newaxis] == [[2, 3, 4]]).all()

    def test_scalar(self):
        from numpypy import array, dtype
        a = array(3)
        raises(IndexError, "a[0]")
        raises(IndexError, "a[0] = 5")
        assert a.size == 1
        assert a.shape == ()
        assert a.dtype is dtype(int)

    def test_len(self):
        from numpypy import array
        a = array(range(5))
        assert len(a) == 5
        assert len(a + a) == 5

    def test_shape(self):
        from numpypy import array
        a = array(range(5))
        assert a.shape == (5,)
        b = a + a
        assert b.shape == (5,)
        c = a[:3]
        assert c.shape == (3,)
        assert array([]).shape == (0,)

    def test_set_shape(self):
        from numpypy import array, zeros
        a = array([])
        raises(ValueError, "a.shape = []")
        a = array(range(12))
        a.shape = (3, 4)
        assert (a == [range(4), range(4, 8), range(8, 12)]).all()
        a.shape = (3, 2, 2)
        assert a[1, 1, 1] == 7
        a.shape = (3, -1, 2)
        assert a.shape == (3, 2, 2)
        a.shape = 12
        assert a.shape == (12, )
        exc = raises(ValueError, "a.shape = 10")
        assert str(exc.value) == "total size of new array must be unchanged"
        a = array(3)
        a.shape = ()
        #numpy allows this
        a.shape = (1,)
        assert a[0] == 3
        a = array(range(6)).reshape(2,3).T
        raises(AttributeError, 'a.shape = 6')

    def test_reshape(self):
        from numpypy import array, zeros
        for a in [array(1), array([1])]:
            for s in [(), (1,)]:
                b = a.reshape(s)
                assert b.shape == s
                assert (b == [1]).all()
        a = array(range(12))
        exc = raises(ValueError, "b = a.reshape(())")
        assert str(exc.value) == "total size of new array must be unchanged"
        exc = raises(ValueError, "b = a.reshape((3, 10))")
        assert str(exc.value) == "total size of new array must be unchanged"
        b = a.reshape((3, 4))
        assert b.shape == (3, 4)
        assert (b == [range(4), range(4, 8), range(8, 12)]).all()
        b[:, 0] = 1000
        assert (a == [1000, 1, 2, 3, 1000, 5, 6, 7, 1000, 9, 10, 11]).all()
        a = zeros((4, 2, 3))
        a.shape = (12, 2)
        (a + a).reshape(2, 12) # assert did not explode
        a = array([[[[]]]])
        assert a.reshape((0,)).shape == (0,)
        assert a.reshape((0,), order='C').shape == (0,)
        assert a.reshape((0,), order='A').shape == (0,)
        raises(TypeError, a.reshape, (0,), badarg="C")
        raises(ValueError, a.reshape, (0,), order="K")
        import sys
        if '__pypy__' in sys.builtin_module_names:
            raises(NotImplementedError, a.reshape, (0,), order='F')

    def test_slice_reshape(self):
        from numpypy import zeros, arange
        a = zeros((4, 2, 3))
        b = a[::2, :, :]
        b.shape = (2, 6)
        exc = raises(AttributeError, "b.shape = 12")
        assert str(exc.value) == \
                           "incompatible shape for a non-contiguous array"
        b = a[::2, :, :].reshape((2, 6))
        assert b.shape == (2, 6)
        b = arange(20)[1:17:2]
        b.shape = (4, 2)
        assert (b == [[1, 3], [5, 7], [9, 11], [13, 15]]).all()
        c = b.reshape((2, 4))
        assert (c == [[1, 3, 5, 7], [9, 11, 13, 15]]).all()

        z = arange(96).reshape((12, -1))
        assert z.shape == (12, 8)
        y = z.reshape((4, 3, 8))
        v = y[:, ::2, :]
        w = y.reshape(96)
        u = v.reshape(64)
        assert y[1, 2, 1] == z[5, 1]
        y[1, 2, 1] = 1000
        # z, y, w, v are views of eachother
        assert z[5, 1] == 1000
        assert v[1, 1, 1] == 1000
        assert w[41] == 1000
        # u is not a view, it is a copy!
        assert u[25] == 41

        a = zeros((5, 2))
        assert a.reshape(-1).shape == (10,)

        raises(ValueError, arange(10).reshape, (5, -1, -1))

    def test_reshape_varargs(self):
        from numpypy import arange
        z = arange(96).reshape(12, -1)
        y = z.reshape(4, 3, 8)
        assert y.shape == (4, 3, 8)

    def test_scalar_reshape(self):
        from numpypy import array
        a = array(3)
        assert a.reshape([1, 1]).shape == (1, 1)
        assert a.reshape([1]).shape == (1,)
        raises(ValueError, "a.reshape(3)")

    def test_strides(self):
        from numpypy import array
        a = array([[1.0, 2.0],
                   [3.0, 4.0]])
        assert a.strides == (16, 8)
        assert a[1:].strides == (16, 8)

    def test_strides_scalar(self):
        from numpypy import array
        a = array(42)
        assert a.strides == ()

    def test_add(self):
        from numpypy import array
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
        from numpypy import array
        a = array(range(5))
        b = array([i for i in reversed(range(5))])
        c = a + b
        for i in range(5):
            assert c[i] == 4

    def test_add_constant(self):
        from numpypy import array
        a = array(range(5))
        b = a + 5
        for i in range(5):
            assert b[i] == i + 5

    def test_radd(self):
        from numpypy import array
        r = 3 + array(range(3))
        for i in range(3):
            assert r[i] == i + 3
        r = [1, 2] + array([1, 2])
        assert (r == [2, 4]).all()

    def test_inline_op_scalar(self):
        from numpypy import array
        for op in [
                '__iadd__',
                '__isub__',
                '__imul__',
                '__idiv__',
                '__ifloordiv__',
                '__imod__',
                '__ipow__',
                '__ilshift__',
                '__irshift__',
                '__iand__',
                '__ior__',
                '__ixor__']:
            a = b = array(range(3))
            getattr(a, op).__call__(2)
            assert id(a) == id(b)

    def test_inline_op_array(self):
        from numpypy import array
        for op in [
                '__iadd__',
                '__isub__',
                '__imul__',
                '__idiv__',
                '__ifloordiv__',
                '__imod__',
                '__ipow__',
                '__ilshift__',
                '__irshift__',
                '__iand__',
                '__ior__',
                '__ixor__']:
            a = b = array(range(5))
            c = array(range(5))
            d = array(5 * [2])
            getattr(a, op).__call__(d)
            assert id(a) == id(b)
            reg_op = op.replace('__i', '__')
            for i in range(5):
                assert a[i] == getattr(c[i], reg_op).__call__(d[i])

    def test_add_list(self):
        from numpypy import array, ndarray
        a = array(range(5))
        b = list(reversed(range(5)))
        c = a + b
        assert isinstance(c, ndarray)
        for i in range(5):
            assert c[i] == 4

    def test_subtract(self):
        from numpypy import array
        a = array(range(5))
        b = a - a
        for i in range(5):
            assert b[i] == 0

    def test_subtract_other(self):
        from numpypy import array
        a = array(range(5))
        b = array([1, 1, 1, 1, 1])
        c = a - b
        for i in range(5):
            assert c[i] == i - 1

    def test_subtract_constant(self):
        from numpypy import array
        a = array(range(5))
        b = a - 5
        for i in range(5):
            assert b[i] == i - 5

    def test_scalar_subtract(self):
        from numpypy import dtype
        int32 = dtype('int32').type
        assert int32(2) - 1 == 1
        assert 1 - int32(2) == -1

    def test_mul(self):
        import numpypy

        a = numpypy.array(range(5))
        b = a * a
        for i in range(5):
            assert b[i] == i * i
        assert b.dtype is a.dtype

        a = numpypy.array(range(5), dtype=bool)
        b = a * a
        assert b.dtype is numpypy.dtype(bool)
        bool_ = numpypy.dtype(bool).type
        assert b[0] is bool_(False)
        for i in range(1, 5):
            assert b[i] is bool_(True)

    def test_mul_constant(self):
        from numpypy import array
        a = array(range(5))
        b = a * 5
        for i in range(5):
            assert b[i] == i * 5

    def test_div(self):
        from math import isnan
        from numpypy import array, dtype

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
        assert c[0] == float('-inf')
        assert isnan(c[1])
        assert c[2] == float('inf')

        b = array([-0.0, -0.0, -0.0])
        c = a / b
        assert c[0] == float('inf')
        assert isnan(c[1])
        assert c[2] == float('-inf')

    def test_div_other(self):
        from numpypy import array
        a = array(range(5))
        b = array([2, 2, 2, 2, 2], float)
        c = a / b
        for i in range(5):
            assert c[i] == i / 2.0

    def test_div_constant(self):
        from numpypy import array
        a = array(range(5))
        b = a / 5.0
        for i in range(5):
            assert b[i] == i / 5.0

    def test_floordiv(self):
        from math import isnan
        from numpypy import array, dtype

        a = array(range(1, 6))
        b = a // a
        assert (b == [1, 1, 1, 1, 1]).all()

        a = array(range(1, 6), dtype=bool)
        b = a // a
        assert b.dtype is dtype("int8")
        assert (b == [1, 1, 1, 1, 1]).all()

        a = array([-1, 0, 1])
        b = array([0, 0, 0])
        c = a // b
        assert (c == [0, 0, 0]).all()

        a = array([-1.0, 0.0, 1.0])
        b = array([0.0, 0.0, 0.0])
        c = a // b
        assert c[0] == float('-inf')
        assert isnan(c[1])
        assert c[2] == float('inf')

        b = array([-0.0, -0.0, -0.0])
        c = a // b
        assert c[0] == float('inf')
        assert isnan(c[1])
        assert c[2] == float('-inf')

    def test_floordiv_other(self):
        from numpypy import array
        a = array(range(5))
        b = array([2, 2, 2, 2, 2], float)
        c = a // b
        assert (c == [0, 0, 1, 1, 2]).all()

    def test_rfloordiv(self):
        from numpypy import array
        a = array(range(1, 6))
        b = 3 // a
        assert (b == [3, 1, 1, 0, 0]).all()

    def test_floordiv_constant(self):
        from numpypy import array
        a = array(range(5))
        b = a // 2
        assert (b == [0, 0, 1, 1, 2]).all()

    def test_signed_integer_division_overflow(self):
        import numpypy as np
        for s in (8, 16, 32, 64):
            for o in ['__div__', '__floordiv__']:
                a = np.array([-2**(s-1)], dtype='int%d' % s)
                assert getattr(a, o)(-1) == 0

    def test_truediv(self):
        from operator import truediv
        from numpypy import arange

        assert (truediv(arange(5), 2) == [0., .5, 1., 1.5, 2.]).all()
        assert (truediv(2, arange(3)) == [float("inf"), 2., 1.]).all()

    def test_divmod(self):
        from numpypy import arange

        a, b = divmod(arange(10), 3)
        assert (a == [0, 0, 0, 1, 1, 1, 2, 2, 2, 3]).all()
        assert (b == [0, 1, 2, 0, 1, 2, 0, 1, 2, 0]).all()

    def test_rdivmod(self):
        from numpypy import arange

        a, b = divmod(3, arange(1, 5))
        assert (a == [3, 1, 1, 0]).all()
        assert (b == [0, 1, 0, 3]).all()

    def test_lshift(self):
        from numpypy import array

        a = array([0, 1, 2, 3])
        assert (a << 2 == [0, 4, 8, 12]).all()
        a = array([True, False])
        assert (a << 2 == [4, 0]).all()
        a = array([1.0])
        raises(TypeError, lambda: a << 2)

    def test_rlshift(self):
        from numpypy import arange

        a = arange(3)
        assert (2 << a == [2, 4, 8]).all()

    def test_rshift(self):
        from numpypy import arange, array

        a = arange(10)
        assert (a >> 2 == [0, 0, 0, 0, 1, 1, 1, 1, 2, 2]).all()
        a = array([True, False])
        assert (a >> 1 == [0, 0]).all()
        a = arange(3, dtype=float)
        raises(TypeError, lambda: a >> 1)

    def test_rrshift(self):
        from numpypy import arange

        a = arange(5)
        assert (2 >> a == [2, 1, 0, 0, 0]).all()

    def test_pow(self):
        from numpypy import array
        a = array(range(5), float)
        b = a ** a
        for i in range(5):
            assert b[i] == i ** i

        a = array(range(5))
        assert (a ** 2 == a * a).all()

    def test_pow_other(self):
        from numpypy import array
        a = array(range(5), float)
        b = array([2, 2, 2, 2, 2])
        c = a ** b
        for i in range(5):
            assert c[i] == i ** 2

    def test_pow_constant(self):
        from numpypy import array
        a = array(range(5), float)
        b = a ** 2
        for i in range(5):
            assert b[i] == i ** 2

    def test_mod(self):
        from numpypy import array
        a = array(range(1, 6))
        b = a % a
        for i in range(5):
            assert b[i] == 0

        a = array(range(1, 6), float)
        b = (a + 1) % a
        assert b[0] == 0
        for i in range(1, 5):
            assert b[i] == 1

    def test_mod_other(self):
        from numpypy import array
        a = array(range(5))
        b = array([2, 2, 2, 2, 2])
        c = a % b
        for i in range(5):
            assert c[i] == i % 2

    def test_mod_constant(self):
        from numpypy import array
        a = array(range(5))
        b = a % 2
        for i in range(5):
            assert b[i] == i % 2

    def test_rand(self):
        from numpypy import arange

        a = arange(5)
        assert (3 & a == [0, 1, 2, 3, 0]).all()

    def test_ror(self):
        from numpypy import arange

        a = arange(5)
        assert (3 | a == [3, 3, 3, 3, 7]).all()

    def test_xor(self):
        from numpypy import arange

        a = arange(5)
        assert (a ^ 3 == [3, 2, 1, 0, 7]).all()

    def test_rxor(self):
        from numpypy import arange

        a = arange(5)
        assert (3 ^ a == [3, 2, 1, 0, 7]).all()

    def test_pos(self):
        from numpypy import array
        a = array([1., -2., 3., -4., -5.])
        b = +a
        for i in range(5):
            assert b[i] == a[i]

        a = +array(range(5))
        for i in range(5):
            assert a[i] == i

    def test_neg(self):
        from numpypy import array
        a = array([1., -2., 3., -4., -5.])
        b = -a
        for i in range(5):
            assert b[i] == -a[i]

        a = -array(range(5), dtype="int8")
        for i in range(5):
            assert a[i] == -i

    def test_abs(self):
        from numpypy import array
        a = array([1., -2., 3., -4., -5.])
        b = abs(a)
        for i in range(5):
            assert b[i] == abs(a[i])

        a = abs(array(range(-5, 5), dtype="int8"))
        for i in range(-5, 5):
            assert a[i + 5] == abs(i)

    def test_auto_force(self):
        from numpypy import array
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
        from numpypy import array
        a = array(range(5))
        s = a[1:5]
        assert len(s) == 4
        for i in range(4):
            assert s[i] == a[i + 1]

        s = (a + a)[1:2]
        assert len(s) == 1
        assert s[0] == 2
        s[:1] = array([5])
        assert s[0] == 5

    def test_getslice_step(self):
        from numpypy import array
        a = array(range(10))
        s = a[1:9:2]
        assert len(s) == 4
        for i in range(4):
            assert s[i] == a[2 * i + 1]

    def test_slice_update(self):
        from numpypy import array
        a = array(range(5))
        s = a[0:3]
        s[1] = 10
        assert a[1] == 10
        a[2] = 20
        assert s[2] == 20

    def test_slice_invaidate(self):
        # check that slice shares invalidation list with
        from numpypy import array
        a = array(range(5))
        s = a[0:2]
        b = array([10, 11])
        c = s + b
        a[0] = 100
        assert c[0] == 10
        assert c[1] == 12
        d = s + b
        a[1] = 101
        assert d[0] == 110
        assert d[1] == 12

    def test_sum(self):
        from numpypy import array, zeros
        a = array(range(5))
        assert a.sum() == 10
        assert a[:4].sum() == 6

        a = array([True] * 5, bool)
        assert a.sum() == 5

        raises(TypeError, 'a.sum(axis=0, out=3)')
        raises(ValueError, 'a.sum(axis=2)')
        d = array(0.)
        b = a.sum(out=d)
        assert b == d
        assert b is d

        assert list(zeros((0, 2)).sum(axis=1)) == []

    def test_reduce_nd(self):
        from numpypy import arange, array
        a = arange(15).reshape(5, 3)
        assert a.sum() == 105
        assert a.max() == 14
        assert array([]).sum() == 0.0
        raises(ValueError, 'array([]).max()')
        assert (a.sum(0) == [30, 35, 40]).all()
        assert (a.sum(axis=0) == [30, 35, 40]).all()
        assert (a.sum(1) == [3, 12, 21, 30, 39]).all()
        assert (a.sum(-1) == a.sum(-1)).all()
        assert (a.sum(-2) == a.sum(-2)).all()
        raises(ValueError, a.sum, -3)
        raises(ValueError, a.sum, 2)
        assert (a.max(0) == [12, 13, 14]).all()
        assert (a.max(1) == [2, 5, 8, 11, 14]).all()
        assert ((a + a).max() == 28)
        assert ((a + a).max(0) == [24, 26, 28]).all()
        assert ((a + a).sum(1) == [6, 24, 42, 60, 78]).all()
        a = array(range(105)).reshape(3, 5, 7)
        assert (a[:, 1, :].sum(0) == [126, 129, 132, 135, 138, 141, 144]).all()
        assert (a[:, 1, :].sum(1) == [70, 315, 560]).all()
        raises (ValueError, 'a[:, 1, :].sum(2)')
        assert ((a + a).T.sum(2).T == (a + a).sum(0)).all()
        assert (a.reshape(1,-1).sum(0) == range(105)).all()
        assert (a.reshape(1,-1).sum(1) == 5460)
        assert (array([[1,2],[3,4]]).prod(0) == [3, 8]).all()
        assert (array([[1,2],[3,4]]).prod(1) == [2, 12]).all()

    def test_prod(self):
        from numpypy import array
        a = array(range(1, 6))
        assert a.prod() == 120.0
        assert a[:4].prod() == 24.0

    def test_max(self):
        from numpypy import array, zeros
        a = array([-1.2, 3.4, 5.7, -3.0, 2.7])
        assert a.max() == 5.7
        b = array([])
        raises(ValueError, "b.max()")
        assert list(zeros((0, 2)).max(axis=1)) == []

    def test_max_add(self):
        from numpypy import array
        a = array([-1.2, 3.4, 5.7, -3.0, 2.7])
        assert (a + a).max() == 11.4

    def test_min(self):
        from numpypy import array, zeros
        a = array([-1.2, 3.4, 5.7, -3.0, 2.7])
        assert a.min() == -3.0
        b = array([])
        raises(ValueError, "b.min()")
        assert list(zeros((0, 2)).min(axis=1)) == []

    def test_argmax(self):
        from numpypy import array
        a = array([-1.2, 3.4, 5.7, -3.0, 2.7])
        r = a.argmax()
        assert r == 2
        b = array([])
        raises(ValueError, b.argmax)

        a = array(range(-5, 5))
        r = a.argmax()
        assert r == 9
        b = a[::2]
        r = b.argmax()
        assert r == 4
        r = (a + a).argmax()
        assert r == 9
        a = array([1, 0, 0])
        assert a.argmax() == 0
        a = array([0, 0, 1])
        assert a.argmax() == 2

        a = array([[1, 2], [3, 4], [5, 6]])
        assert a.argmax() == 5
        assert a.argmax(axis=None, out=None) == 5
        assert a[:2, ].argmax() == 3
        import sys
        if '__pypy__' in sys.builtin_module_names:
            raises(NotImplementedError, a.argmax, axis=0)

    def test_argmin(self):
        from numpypy import array
        a = array([-1.2, 3.4, 5.7, -3.0, 2.7])
        assert a.argmin() == 3
        assert a.argmin(axis=None, out=None) == 3
        b = array([])
        raises(ValueError, "b.argmin()")
        import sys
        if '__pypy__' in sys.builtin_module_names:
            raises(NotImplementedError, a.argmin, axis=0)

    def test_all(self):
        from numpypy import array
        a = array(range(5))
        assert a.all() == False
        a[0] = 3.0
        assert a.all() == True
        b = array([])
        assert b.all() == True

    def test_any(self):
        from numpypy import array, zeros
        a = array(range(5))
        assert a.any() == True
        b = zeros(5)
        assert b.any() == False
        c = array([])
        assert c.any() == False

    def test_dtype_guessing(self):
        from numpypy import array, dtype

        assert array([True]).dtype is dtype(bool)
        assert array([True, False]).dtype is dtype(bool)
        assert array([True, 1]).dtype is dtype(int)
        assert array([1, 2, 3]).dtype is dtype(int)
        #assert array([1L, 2, 3]).dtype is dtype(long)
        assert array([1.2, True]).dtype is dtype(float)
        assert array([1.2, 5]).dtype is dtype(float)
        assert array([]).dtype is dtype(float)
        float64 = dtype('float64').type
        int8 = dtype('int8').type
        bool_ = dtype('bool').type
        assert array([float64(2)]).dtype is dtype(float)
        assert array([int8(3)]).dtype is dtype("int8")
        assert array([bool_(True)]).dtype is dtype(bool)
        assert array([bool_(True), 3.0]).dtype is dtype(float)

    def test_comparison(self):
        import operator
        from numpypy import array, dtype

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

    def test___nonzero__(self):
        from numpypy import array
        a = array([1, 2])
        raises(ValueError, bool, a)
        raises(ValueError, bool, a == a)
        assert bool(array(1))
        assert not bool(array(0))
        assert bool(array([1]))
        assert not bool(array([0]))

    def test_slice_assignment(self):
        from numpypy import array
        a = array(range(5))
        a[::-1] = a
        assert (a == [4, 3, 2, 1, 0]).all()
        # but we force intermediates
        a = array(range(5))
        a[::-1] = a + a
        assert (a == [8, 6, 4, 2, 0]).all()

    def test_virtual_views(self):
        from numpypy import arange
        a = arange(15)
        c = (a + a)
        d = c[::2]
        assert d[3] == 12
        c[6] = 5
        assert d[3] == 5
        a = arange(15)
        c = (a + a)
        d = c[::2][::2]
        assert d[1] == 8
        b = a + a
        c = b[::2]
        c[:] = 3
        assert b[0] == 3
        assert b[1] == 2

    def test_realimag_views(self):
        from numpypy import arange, array
        a = arange(15)
        b = a.real
        b[5]=50
        assert a[5] == 50
        b = a.imag
        assert b[7] == 0
        raises(ValueError, 'b[7] = -2')
        raises(TypeError, 'a.imag = -2')
        a = array(['abc','def'],dtype='S3')
        b = a.real
        assert a[0] == b[0]
        assert a[1] == b[1]
        b[1] = 'xyz'
        assert a[1] == 'xyz'
        assert a.imag[0] == ''
        raises(TypeError, 'a.imag = "qop"')
        a=array([[1+1j, 2-3j, 4+5j],[-6+7j, 8-9j, -2-1j]])
        assert a.real[0,1] == 2
        a.real[0,1] = -20
        assert a[0,1].real == -20
        b = a.imag
        assert b[1,2] == -1
        b[1,2] = 30
        assert a[1,2].imag == 30
        a.real = 13
        assert a[1,1].real == 13
        a=array([1+1j, 2-3j, 4+5j, -6+7j, 8-9j, -2-1j])
        a.real = 13
        assert a[3].real == 13
        a.imag = -5
        a.imag[3] = -10
        assert a[3].imag == -10
        assert a[2].imag == -5

        assert arange(4, dtype='>c8').imag.max() == 0.0
        assert arange(4, dtype='<c8').imag.max() == 0.0
        assert arange(4, dtype='>c8').real.max() == 3.0
        assert arange(4, dtype='<c8').real.max() == 3.0

    def test_view(self):
        from numpypy import array, dtype
        x = array((1, 2), dtype='int8')
        assert x.shape == (2,)
        y = x.view(dtype='int16')
        assert x.shape == (2,)
        assert y[0] == 513
        assert y.dtype == dtype('int16')
        y[0] = 670
        assert x[0] == -98
        assert x[1] == 2
        f = array([1000, -1234], dtype='i4')
        nnp = self.non_native_prefix
        d = f.view(dtype=nnp + 'i4')
        assert (d == [-402456576,  788267007]).all()
        x = array(range(15), dtype='i2').reshape(3,5)
        exc = raises(ValueError, x.view, dtype='i4')
        assert exc.value[0] == "new type not compatible with array."
        assert x.view('int8').shape == (3, 10)
        x = array(range(15), dtype='int16').reshape(3,5).T
        assert x.view('int8').shape == (10, 3)

    def test_ndarray_view_empty(self):
        from numpypy import array, dtype
        x = array([], dtype=[('a', 'int8'), ('b', 'int8')])
        y = x.view(dtype='int16')

    def test_scalar_view(self):
        from numpypy import dtype, array
        a = array(0, dtype='int32')
        b = a.view(dtype='float32')
        assert b.shape == ()
        assert b == 0
        s = dtype('int64').type(12)
        exc = raises(ValueError, s.view, 'int8')
        assert exc.value[0] == "new type not compatible with array."
        skip('not implemented yet')
        assert s.view('double') < 7e-323

    def test_tolist_scalar(self):
        from numpypy import dtype
        int32 = dtype('int32').type
        bool_ = dtype('bool').type
        x = int32(23)
        assert x.tolist() == 23
        assert type(x.tolist()) is int
        y = bool_(True)
        assert y.tolist() is True

    def test_tolist_zerodim(self):
        from numpypy import array
        x = array(3)
        assert x.tolist() == 3
        assert type(x.tolist()) is int

    def test_tolist_singledim(self):
        from numpypy import array
        a = array(range(5))
        assert a.tolist() == [0, 1, 2, 3, 4]
        assert type(a.tolist()[0]) is int
        b = array([0.2, 0.4, 0.6])
        assert b.tolist() == [0.2, 0.4, 0.6]

    def test_tolist_multidim(self):
        from numpypy import array
        a = array([[1, 2], [3, 4]])
        assert a.tolist() == [[1, 2], [3, 4]]

    def test_tolist_view(self):
        from numpypy import array
        a = array([[1, 2], [3, 4]])
        assert (a + a).tolist() == [[2, 4], [6, 8]]

    def test_tolist_slice(self):
        from numpypy import array
        a = array([[17.1, 27.2], [40.3, 50.3]])
        assert a[:, 0].tolist() == [17.1, 40.3]
        assert a[0].tolist() == [17.1, 27.2]

    def test_concatenate(self):
        from numpypy import array, concatenate, dtype
        a1 = array([0,1,2])
        a2 = array([3,4,5])
        a = concatenate((a1, a2))
        assert len(a) == 6
        assert (a == [0,1,2,3,4,5]).all()
        assert a.dtype is dtype(int)
        if 0: # XXX why does numpy allow this?
            a = concatenate((a1, a2), axis=1)
            assert (a == [0,1,2,3,4,5]).all()
        a = concatenate((a1, a2), axis=-1)
        assert (a == [0,1,2,3,4,5]).all()

        b1 = array([[1, 2], [3, 4]])
        b2 = array([[5, 6]])
        b = concatenate((b1, b2), axis=0)
        assert (b == [[1, 2],[3, 4],[5, 6]]).all()
        c = concatenate((b1, b2.T), axis=1)
        assert (c == [[1, 2, 5],[3, 4, 6]]).all()
        d = concatenate(([0],[1]))
        assert (d == [0,1]).all()
        e1 = array([[0,1],[2,3]])
        e = concatenate(e1)
        assert (e == [0,1,2,3]).all()
        f1 = array([0,1])
        f = concatenate((f1, [2], f1, [7]))
        assert (f == [0,1,2,0,1,7]).all()

        g1 = array([[0,1,2]])
        g2 = array([[3,4,5]])
        g = concatenate((g1, g2), axis=-2)
        assert (g == [[0,1,2],[3,4,5]]).all()
        exc = raises(IndexError, concatenate, (g1, g2), axis=-3)
        assert str(exc.value) == "axis -3 out of bounds [0, 2)"
        exc = raises(IndexError, concatenate, (g1, g2), axis=2)
        assert str(exc.value) == "axis 2 out of bounds [0, 2)"

        exc = raises(ValueError, concatenate, ())
        assert str(exc.value) == \
                "need at least one array to concatenate"

        exc = raises(ValueError, concatenate, (a1, b1), axis=0)
        assert str(exc.value) == \
                "all the input arrays must have same number of dimensions"

        g1 = array([0,1,2])
        g2 = array([[3,4,5]])
        exc = raises(ValueError, concatenate, (g1, g2), axis=2)
        assert str(exc.value) == \
                "all the input arrays must have same number of dimensions"

        a = array([1, 2, 3, 4, 5, 6])
        a = (a + a)[::2]
        b = concatenate((a[:3], a[-3:]))
        assert (b == [2, 6, 10, 2, 6, 10]).all()
        a = concatenate((array([1]), array(['abc'])))
        assert str(a.dtype) == '|S3'
        a = concatenate((array([]), array(['abc'])))
        assert a[0] == 'abc'
        a = concatenate((['abcdef'], ['abc']))
        assert a[0] == 'abcdef'
        assert str(a.dtype) == '|S6'

    def test_record_concatenate(self):
        # only an exact match can succeed
        from numpypy import zeros, concatenate
        a = concatenate((zeros((2,),dtype=[('x', int), ('y', float)]),
                         zeros((2,),dtype=[('x', int), ('y', float)])))
        assert a.shape == (4,)
        exc = raises(TypeError, concatenate,
                            (zeros((2,), dtype=[('x', int), ('y', float)]),
                            (zeros((2,), dtype=[('x', float), ('y', float)]))))
        assert str(exc.value).startswith('invalid type promotion')
        exc = raises(TypeError, concatenate, ([1], zeros((2,),
                                            dtype=[('x', int), ('y', float)])))
        assert str(exc.value).startswith('invalid type promotion')
        exc = raises(TypeError, concatenate, (['abc'], zeros((2,),
                                            dtype=[('x', int), ('y', float)])))
        assert str(exc.value).startswith('invalid type promotion')

    def test_flatten(self):
        from numpypy import array

        assert array(3).flatten().shape == (1,)
        a = array([[1, 2], [3, 4]])
        b = a.flatten()
        c = a.ravel()
        a[0, 0] = 15
        assert b[0] == 1
        assert c[0] == 15
        a = array([[1, 2, 3], [4, 5, 6]])
        assert (a.flatten() == [1, 2, 3, 4, 5, 6]).all()
        a = array([[[1, 2], [3, 4]], [[5, 6], [7, 8]]])
        assert (a.flatten() == [1, 2, 3, 4, 5, 6, 7, 8]).all()
        a = array([1, 2, 3, 4, 5, 6, 7, 8])
        assert (a[::2].flatten() == [1, 3, 5, 7]).all()
        a = array([1, 2, 3])
        assert ((a + a).flatten() == [2, 4, 6]).all()
        a = array(2)
        assert (a.flatten() == [2]).all()
        a = array([[1, 2], [3, 4]])
        assert (a.T.flatten() == [1, 3, 2, 4]).all()

    def test_itemsize(self):
        from numpypy import ones, dtype, array

        for obj in [float, bool, int]:
            assert ones(1, dtype=obj).itemsize == dtype(obj).itemsize
        assert (ones(1) + ones(1)).itemsize == 8
        assert array(1.0).itemsize == 8
        assert ones(1)[:].itemsize == 8

    def test_nbytes(self):
        from numpypy import array, ones

        assert ones(1).nbytes == 8
        assert ones((2, 2)).nbytes == 32
        assert ones((2, 2))[1:,].nbytes == 16
        assert (ones(1) + ones(1)).nbytes == 8
        assert array(3.0).nbytes == 8

    def test_repeat(self):
        from numpypy import array
        a = array([[1, 2], [3, 4]])
        assert (a.repeat(3) == [1, 1, 1, 2, 2, 2,
                                 3, 3, 3, 4, 4, 4]).all()
        assert (a.repeat(2, axis=0) == [[1, 2], [1, 2], [3, 4],
                                         [3, 4]]).all()
        assert (a.repeat(2, axis=1) == [[1, 1, 2, 2], [3, 3,
                                                        4, 4]]).all()
        assert (array([1, 2]).repeat(2) == array([1, 1, 2, 2])).all()

    def test_resize(self):
        import numpy as np
        a = np.array([1,2,3])
        import sys
        if '__pypy__' in sys.builtin_module_names:
            raises(NotImplementedError, a.resize, ())

    def test_squeeze(self):
        import numpy as np
        a = np.array([1,2,3])
        assert a.squeeze() is a
        a = np.array([[1,2,3]])
        b = a.squeeze()
        assert b.shape == (3,)
        assert (b == a).all()
        b[1] = -1
        assert a[0][1] == -1

    def test_swapaxes(self):
        from numpypy import array
        # testcases from numpy docstring
        x = array([[1, 2, 3]])
        assert (x.swapaxes(0, 1) == array([[1], [2], [3]])).all()
        x = array([[[0,1],[2,3]],[[4,5],[6,7]]]) # shape = (2, 2, 2)
        assert (x.swapaxes(0, 2) == array([[[0, 4], [2, 6]],
                                           [[1, 5], [3, 7]]])).all()
        assert (x.swapaxes(0, 1) == array([[[0, 1], [4, 5]],
                                           [[2, 3], [6, 7]]])).all()
        assert (x.swapaxes(1, 2) == array([[[0, 2], [1, 3]],
                                           [[4, 6],[5, 7]]])).all()

        # more complex shape i.e. (2, 2, 3)
        x = array([[[1, 2, 3], [4, 5, 6]], [[7, 8, 9], [10, 11, 12]]])
        assert (x.swapaxes(0, 1) == array([[[1, 2, 3], [7, 8, 9]],
                                           [[4, 5, 6], [10, 11, 12]]])).all()
        assert (x.swapaxes(0, 2) == array([[[1, 7], [4, 10]], [[2, 8], [5, 11]],
                                           [[3, 9], [6, 12]]])).all()
        assert (x.swapaxes(1, 2) == array([[[1, 4], [2, 5], [3, 6]],
                                           [[7, 10], [8, 11],[9, 12]]])).all()

        # test slice
        assert (x[0:1,0:2].swapaxes(0,2) == array([[[1], [4]], [[2], [5]],
                                                   [[3], [6]]])).all()
        # test virtual
        assert ((x + x).swapaxes(0,1) == array([[[ 2,  4,  6], [14, 16, 18]],
                                         [[ 8, 10, 12], [20, 22, 24]]])).all()
        assert array(1).swapaxes(10, 12) == 1

    def test_filter_bug(self):
        from numpypy import array
        a = array([1.0,-1.0])
        a[a<0] = -a[a<0]
        assert (a == [1, 1]).all()

    def test_int_list_index(slf):
        from numpypy import array, arange
        assert (array([10,11,12,13])[[1,2]] == [11, 12]).all()
        assert (arange(6).reshape((2,3))[[0,1]] == [[0, 1, 2], [3, 4, 5]]).all()
        assert arange(6).reshape((2,3))[(0,1)] == 1

    def test_int_array_index(self):
        from numpypy import array, arange, zeros
        b = arange(10)[array([3, 2, 1, 5])]
        assert (b == [3, 2, 1, 5]).all()
        raises(IndexError, "arange(10)[array([10])]")
        assert (arange(10)[[-5, -3]] == [5, 7]).all()
        raises(IndexError, "arange(10)[[-11]]")
        a = arange(1)
        a[[0, 0]] += 1
        assert a[0] == 1
        assert (zeros(1)[[]] == []).all()

    def test_int_array_index_setitem(self):
        from numpypy import arange, zeros, array
        a = arange(10)
        a[[3, 2, 1, 5]] = zeros(4, dtype=int)
        assert (a == [0, 0, 0, 0, 4, 0, 6, 7, 8, 9]).all()
        a[[-9, -8]] = [1, 1]
        assert (a == [0, 1, 1, 0, 4, 0, 6, 7, 8, 9]).all()
        raises(IndexError, "arange(10)[array([10])] = 3")
        raises(IndexError, "arange(10)[[-11]] = 3")

    def test_bool_single_index(self):
        import numpypy as np
        a = np.array([[1, 2, 3],
                      [4, 5, 6],
                      [7, 8, 9]])
        a[np.array(True)]; skip("broken")  # check for crash but skip rest of test until correct
        assert (a[np.array(True)] == a[1]).all()
        assert (a[np.array(False)] == a[0]).all()

    def test_bool_array_index(self):
        from numpypy import arange, array
        b = arange(10)
        assert (b[array([True, False, True])] == [0, 2]).all()
        raises(ValueError, "array([1, 2])[array([True, True, True])]")
        raises(ValueError, "b[array([[True, False], [True, False]])]")
        a = array([[1,2,3],[4,5,6],[7,8,9]],int)
        c = array([True,False,True],bool)
        b = a[c]
        assert (a[c] == [[1, 2, 3], [7, 8, 9]]).all()

    def test_bool_array_index_setitem(self):
        from numpypy import arange, array
        b = arange(5)
        b[array([True, False, True])] = [20, 21, 0, 0, 0, 0, 0]
        assert (b == [20, 1, 21, 3, 4]).all()
        raises(ValueError, "array([1, 2])[array([True, False, True])] = [1, 2, 3]")

    def test_weakref(self):
        import _weakref
        from numpypy import array
        a = array([1, 2, 3])
        assert _weakref.ref(a)
        a = array(42)
        assert _weakref.ref(a)

    def test_astype(self):
        from numpypy import array, arange
        b = array(1).astype(float)
        assert b == 1
        assert b.dtype == float
        b = array([1, 2]).astype(float)
        assert (b == [1, 2]).all()
        assert b.dtype == 'float'
        b = array([1, 2], dtype=complex).astype(int)
        assert (b == [1, 2]).all()
        assert b.dtype == 'int'
        b = array([0, 1, 2], dtype=complex).astype(bool)
        assert (b == [False, True, True]).all()
        assert b.dtype == 'bool'

        a = arange(6, dtype='f4').reshape(2,3)
        b = a.astype('i4')

        a = array('x').astype('S3').dtype
        assert a.itemsize == 3
        # scalar vs. array
        a = array([1, 2, 3.14156]).astype('S3').dtype
        assert a.itemsize == 3
        a = array(3.1415).astype('S3').dtype
        assert a.itemsize == 3
        try:
            a = array(['1', '2','3']).astype(float)
            assert a[2] == 3.0
        except NotImplementedError:
            skip('astype("float") not implemented for str arrays')

    def test_base(self):
        from numpypy import array
        assert array(1).base is None
        assert array([1, 2]).base is None
        a = array([1, 2, 3, 4])
        b = a[::2]
        assert b.base is a

    def test_byteswap(self):
        from numpypy import array

        s1 = array(1.).byteswap().tostring()
        s2 = array([1.]).byteswap().tostring()
        assert s1 == s2

        a = array([1, 256 + 2, 3], dtype='i2')
        assert (a.byteswap() == [0x0100, 0x0201, 0x0300]).all()
        assert (a == [1, 256 + 2, 3]).all()
        assert (a.byteswap(True) == [0x0100, 0x0201, 0x0300]).all()
        assert (a == [0x0100, 0x0201, 0x0300]).all()

        a = array([1, -1, 1e300], dtype=float)
        s1 = map(ord, a.tostring())
        s2 = map(ord, a.byteswap().tostring())
        assert a.dtype.itemsize == 8
        for i in range(a.size):
            i1 = i * a.dtype.itemsize
            i2 = (i+1) * a.dtype.itemsize
            assert list(reversed(s1[i1:i2])) == s2[i1:i2]

        a = array([1+1e30j, -1, 1e10], dtype=complex)
        s1 = map(ord, a.tostring())
        s2 = map(ord, a.byteswap().tostring())
        assert a.dtype.itemsize == 16
        for i in range(a.size*2):
            i1 = i * a.dtype.itemsize/2
            i2 = (i+1) * a.dtype.itemsize/2
            assert list(reversed(s1[i1:i2])) == s2[i1:i2]

        a = array([3.14, -1.5, 10000], dtype='float16')
        s1 = map(ord, a.tostring())
        s2 = map(ord, a.byteswap().tostring())
        assert a.dtype.itemsize == 2
        for i in range(a.size):
            i1 = i * a.dtype.itemsize
            i2 = (i+1) * a.dtype.itemsize
            assert list(reversed(s1[i1:i2])) == s2[i1:i2]

        a = array([1, -1, 10000], dtype='longfloat')
        s1 = map(ord, a.tostring())
        s2 = map(ord, a.byteswap().tostring())
        assert a.dtype.itemsize >= 8
        for i in range(a.size):
            i1 = i * a.dtype.itemsize
            i2 = (i+1) * a.dtype.itemsize
            assert list(reversed(s1[i1:i2])) == s2[i1:i2]

    def test_clip(self):
        from numpypy import array
        a = array([1, 2, 17, -3, 12])
        assert (a.clip(-2, 13) == [1, 2, 13, -2, 12]).all()
        assert (a.clip(-1, 1, out=None) == [1, 1, 1, -1, 1]).all()
        assert (a == [1, 2, 17, -3, 12]).all()
        assert (a.clip(-1, [1, 2, 3, 4, 5]) == [1, 2, 3, -1, 5]).all()
        assert (a.clip(-2, 13, out=a) == [1, 2, 13, -2, 12]).all()
        assert (a == [1, 2, 13, -2, 12]).all()

    def test_data(self):
        from numpypy import array
        a = array([1, 2, 3, 4], dtype='i4')
        assert a.data[0] == '\x01'
        assert a.data[1] == '\x00'
        assert a.data[4] == '\x02'
        a.data[4] = '\xff'
        assert a[1] == 0xff
        assert len(a.data) == 16

    def test_explicit_dtype_conversion(self):
        from numpypy import array
        a = array([1.0, 2.0])
        b = array(a, dtype='d')
        assert a.dtype is b.dtype

    def test_notequal_different_shapes(self):
        from numpypy import array
        a = array([1, 2])
        b = array([1, 2, 3, 4])
        assert (a == b) == False

    def test__long__(self):
        from numpypy import array
        assert long(array(1)) == 1
        assert long(array([1])) == 1
        assert isinstance(long(array([1])), long)
        assert isinstance(long(array([1, 2][0])), long)
        assert raises(TypeError, "long(array([1, 2]))")
        assert long(array([1.5])) == 1

    def test__int__(self):
        from numpypy import array
        assert int(array(1)) == 1
        assert int(array([1])) == 1
        assert raises(TypeError, "int(array([1, 2]))")
        assert int(array([1.5])) == 1

    def test__reduce__(self):
        from numpypy import array, dtype
        from cPickle import loads, dumps

        a = array([1, 2], dtype="int64")
        data = a.__reduce__()

        assert data[2][4] == '\x01\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00'

        pickled_data = dumps(a)
        assert (loads(pickled_data) == a).all()

    def test_pickle_slice(self):
        from cPickle import loads, dumps
        import numpypy as numpy

        a = numpy.arange(10.).reshape((5, 2))[::2]
        assert (loads(dumps(a)) == a).all()

    def test_string_filling(self):
        import numpypy as numpy
        a = numpy.empty((10,10), dtype='c1')
        a.fill(12)
        assert (a == '1').all()

    def test_boolean_indexing(self):
        import numpypy as np
        a = np.zeros((1, 3))
        b = np.array([True])

        assert (a[b] == a).all()
        a[b] = 1.
        assert (a == [[1., 1., 1.]]).all()

    @py.test.mark.xfail
    def test_boolean_array(self):
        import numpypy as np
        a = np.ndarray([1], dtype=bool)
        assert a[0] == True

class AppTestMultiDim(BaseNumpyAppTest):
    def test_init(self):
        import numpypy
        a = numpypy.zeros((2, 2))
        assert len(a) == 2

    def test_shape(self):
        import numpypy
        assert numpypy.zeros(1).shape == (1,)
        assert numpypy.zeros((2, 2)).shape == (2, 2)
        assert numpypy.zeros((3, 1, 2)).shape == (3, 1, 2)
        assert numpypy.array([[1], [2], [3]]).shape == (3, 1)
        assert len(numpypy.zeros((3, 1, 2))) == 3
        raises(TypeError, len, numpypy.zeros(()))
        raises(ValueError, numpypy.array, [[1, 2], 3], dtype=float)

    def test_getsetitem(self):
        import numpypy
        a = numpypy.zeros((2, 3, 1))
        raises(IndexError, a.__getitem__, (2, 0, 0))
        raises(IndexError, a.__getitem__, (0, 3, 0))
        raises(IndexError, a.__getitem__, (0, 0, 1))
        assert a[1, 1, 0] == 0
        a[1, 2, 0] = 3
        assert a[1, 2, 0] == 3
        assert a[1, 1, 0] == 0
        assert a[1, -1, 0] == 3

    def test_slices(self):
        import numpypy
        a = numpypy.zeros((4, 3, 2))
        raises(IndexError, a.__getitem__, (4,))
        raises(IndexError, a.__getitem__, (3, 3))
        raises(IndexError, a.__getitem__, (slice(None), 3))
        a[0, 1, 1] = 13
        a[1, 2, 1] = 15
        b = a[0]
        assert len(b) == 3
        assert b.shape == (3, 2)
        assert b[1, 1] == 13
        b = a[1]
        assert b.shape == (3, 2)
        assert b[2, 1] == 15
        b = a[:, 1]
        assert b.shape == (4, 2)
        assert b[0, 1] == 13
        b = a[:, 1, :]
        assert b.shape == (4, 2)
        assert b[0, 1] == 13
        b = a[1, 2]
        assert b[1] == 15
        b = a[:]
        assert b.shape == (4, 3, 2)
        assert b[1, 2, 1] == 15
        assert b[0, 1, 1] == 13
        b = a[:][:, 1][:]
        assert b[2, 1] == 0.0
        assert b[0, 1] == 13
        raises(IndexError, b.__getitem__, (4, 1))
        assert a[0][1][1] == 13
        assert a[1][2][1] == 15

    def test_setitem_slice(self):
        import numpypy
        a = numpypy.zeros((3, 4))
        a[1] = [1, 2, 3, 4]
        assert a[1, 2] == 3
        raises(TypeError, a[1].__setitem__, [1, 2, 3])
        a = numpypy.array([[1, 2], [3, 4]])
        assert (a == [[1, 2], [3, 4]]).all()
        a[1] = numpypy.array([5, 6])
        assert (a == [[1, 2], [5, 6]]).all()
        a[:, 1] = numpypy.array([8, 10])
        assert (a == [[1, 8], [5, 10]]).all()
        a[0, :: -1] = numpypy.array([11, 12])
        assert (a == [[12, 11], [5, 10]]).all()

    def test_ufunc(self):
        from numpypy import array
        a = array([[1, 2], [3, 4], [5, 6]])
        assert ((a + a) == \
            array([[1 + 1, 2 + 2], [3 + 3, 4 + 4], [5 + 5, 6 + 6]])).all()

    def test_getitem_add(self):
        from numpypy import array
        a = array([[1, 2], [3, 4], [5, 6], [7, 8], [9, 10]])
        assert (a + a)[1, 1] == 8

    def test_getitem_3(self):
        from numpypy import array
        a = array([[1, 2], [3, 4], [5, 6], [7, 8],
                   [9, 10], [11, 12], [13, 14]])
        b = a[::2]
        assert (b == [[1, 2], [5, 6], [9, 10], [13, 14]]).all()
        c = b + b
        assert c[1][1] == 12

    def test_multidim_ones(self):
        from numpypy import ones
        a = ones((1, 2, 3))
        assert a[0, 1, 2] == 1.0

    def test_multidim_setslice(self):
        from numpypy import zeros, ones
        a = zeros((3, 3))
        b = ones((3, 3))
        a[:, 1:3] = b[:, 1:3]
        assert (a == [[0, 1, 1], [0, 1, 1], [0, 1, 1]]).all()
        a = zeros((3, 3))
        b = ones((3, 3))
        a[:, ::2] = b[:, ::2]
        assert (a == [[1, 0, 1], [1, 0, 1], [1, 0, 1]]).all()

    def test_broadcast_ufunc(self):
        from numpypy import array
        a = array([[1, 2], [3, 4], [5, 6]])
        b = array([5, 6])
        c = ((a + b) == [[1 + 5, 2 + 6], [3 + 5, 4 + 6], [5 + 5, 6 + 6]])
        assert c.all()

    def test_broadcast_setslice(self):
        from numpypy import zeros, ones
        a = zeros((10, 10))
        b = ones(10)
        a[:, :] = b
        assert a[3, 5] == 1

    def test_broadcast_shape_agreement(self):
        from numpypy import zeros, array
        a = zeros((3, 1, 3))
        b = array(((10, 11, 12), (20, 21, 22), (30, 31, 32)))
        c = ((a + b) == [b, b, b])
        assert c.all()
        a = array((((10, 11, 12), ), ((20, 21, 22), ), ((30, 31, 32), )))
        assert(a.shape == (3, 1, 3))
        d = zeros((3, 3))
        c = ((a + d) == [b, b, b])
        c = ((a + d) == array([[[10., 11., 12.]] * 3,
                               [[20., 21., 22.]] * 3, [[30., 31., 32.]] * 3]))
        assert c.all()

    def test_broadcast_scalar(self):
        from numpypy import zeros
        a = zeros((4, 5), 'd')
        a[:, 1] = 3
        assert a[2, 1] == 3
        assert a[0, 2] == 0
        a[0, :] = 5
        assert a[0, 3] == 5
        assert a[2, 1] == 3
        assert a[3, 2] == 0

    def test_broadcast_call2(self):
        from numpypy import zeros, ones
        a = zeros((4, 1, 5))
        b = ones((4, 3, 5))
        b[:] = (a + a)
        assert (b == zeros((4, 3, 5))).all()

    def test_broadcast_virtualview(self):
        from numpypy import arange, zeros
        a = arange(8).reshape([2, 2, 2])
        b = (a + a)[1, 1]
        c = zeros((2, 2, 2))
        c[:] = b
        assert (c == [[[12, 14], [12, 14]], [[12, 14], [12, 14]]]).all()

    def test_broadcast_wrong_shapes(self):
        from numpypy import zeros
        a = zeros((4, 3, 2))
        b = zeros((4, 2))
        exc = raises(ValueError, lambda: a + b)
        assert str(exc.value).startswith("operands could not be broadcast")

    def test_reduce(self):
        from numpypy import array
        a = array([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]])
        assert a.sum() == (13 * 12) / 2
        b = a[1:, 1::2]
        c = b + b
        assert c.sum() == (6 + 8 + 10 + 12) * 2
        assert isinstance(c.sum(dtype='f8'), float)
        assert isinstance(c.sum(None, 'f8'), float)

    def test_transpose(self):
        from numpypy import array
        a = array(((range(3), range(3, 6)),
                   (range(6, 9), range(9, 12)),
                   (range(12, 15), range(15, 18)),
                   (range(18, 21), range(21, 24))))
        assert a.shape == (4, 2, 3)
        b = a.T
        assert b.shape == (3, 2, 4)
        assert(b[0, :, 0] == [0, 3]).all()
        b[:, 0, 0] = 1000
        assert(a[0, 0, :] == [1000, 1000, 1000]).all()
        a = array(range(5))
        b = a.T
        assert(b == range(5)).all()
        a = array((range(10), range(20, 30)))
        b = a.T
        assert(b[:, 0] == a[0, :]).all()
        assert (a.transpose() == b).all()
        assert (a.transpose(None) == b).all()
        import sys
        if '__pypy__' in sys.builtin_module_names:
            raises(NotImplementedError, a.transpose, (1, 0, 2))

    def test_flatiter(self):
        from numpypy import array, flatiter, arange, zeros
        a = array([[10, 30], [40, 60]])
        f_iter = a.flat
        assert f_iter.next() == 10
        assert f_iter.next() == 30
        assert f_iter.next() == 40
        assert f_iter.next() == 60
        raises(StopIteration, "f_iter.next()")
        raises(TypeError, "flatiter()")
        s = 0
        for k in a.flat:
            s += k
        assert s == 140
        a = arange(10).reshape(5, 2)
        raises(IndexError, 'a.flat[(1, 2)]')
        assert a.flat.base is a
        m = zeros((2,2), dtype='S3')
        m.flat[1] = 1
        assert m[0,1] == '1'

    def test_flatiter_array_conv(self):
        from numpypy import array, dot
        a = array([1, 2, 3])
        assert dot(a.flat, a.flat) == 14

    def test_flatiter_varray(self):
        from numpypy import ones
        a = ones((2, 2))
        assert list(((a + a).flat)) == [2, 2, 2, 2]

    def test_flatiter_getitem(self):
        from numpypy import arange
        a = arange(10)
        assert a.flat[3] == 3
        assert a[2:].flat[3] == 5
        assert (a + a).flat[3] == 6
        assert a[::2].flat[3] == 6
        assert a.reshape(2,5).flat[3] == 3
        b = a.reshape(2,5).flat
        b.next()
        b.next()
        b.next()
        assert b.index == 3
        assert b.coords == (0, 3)
        assert b[3] == 3
        assert (b[::3] == [0, 3, 6, 9]).all()
        assert (b[2::5] == [2, 7]).all()
        assert b[-2] == 8
        raises(IndexError, "b[11]")
        raises(IndexError, "b[-11]")
        raises(IndexError, 'b[0, 1]')
        assert b.index == 0
        assert b.coords == (0, 0)

    def test_flatiter_setitem(self):
        from numpypy import arange, array
        a = arange(12).reshape(3,4)
        b = a.T.flat
        b[6::2] = [-1, -2]
        assert (a == [[0, 1, -1, 3], [4, 5, 6, -1], [8, 9, -2, 11]]).all()
        b[0:2] = [[[100]]]
        assert(a[0,0] == 100)
        assert(a[1,0] == 100)

    def test_flatiter_ops(self):
        from numpypy import arange, array
        a = arange(12).reshape(3,4)
        b = a.T.flat
        assert (b == [0,  4, 8, 1, 5, 9, 2, 6, 10, 3, 7, 11]).all()
        assert not (b != [0,  4, 8, 1, 5, 9, 2, 6, 10, 3, 7, 11]).any()
        assert ((b >= range(12)) == [True, True, True,False, True, True,
                             False, False, True, False, False, True]).all()
        assert ((b < range(12)) != [True, True, True,False, True, True,
                             False, False, True, False, False, True]).all()
        assert ((b <= range(12)) != [False, True, True,False, True, True,
                            False, False, True, False, False, False]).all()
        assert ((b > range(12)) == [False, True, True,False, True, True,
                            False, False, True, False, False, False]).all()

    def test_flatiter_view(self):
        from numpypy import arange
        a = arange(10).reshape(5, 2)
        assert (a[::2].flat == [0, 1, 4, 5, 8, 9]).all()

    def test_flatiter_transpose(self):
        from numpypy import arange
        a = arange(10).reshape(2, 5).T
        b = a.flat
        assert (b[:5] == [0, 5, 1, 6, 2]).all()
        b.next()
        b.next()
        b.next()
        assert b.index == 3
        assert b.coords == (1, 1)

    def test_flatiter_len(self):
        from numpypy import arange

        assert len(arange(10).flat) == 10
        assert len(arange(10).reshape(2, 5).flat) == 10
        assert len(arange(10)[:2].flat) == 2
        assert len((arange(2) + arange(2)).flat) == 2

    def test_flatiter_setter(self):
        from numpypy import arange, array
        a = arange(24).reshape(2, 3, 4)
        a.flat = [4, 5]
        assert (a.flatten() == [4, 5]*12).all()
        a.flat = [[4, 5, 6, 7, 8], [4, 5, 6, 7, 8]]
        assert (a.flatten() == ([4, 5, 6, 7, 8]*5)[:24]).all()
        exc = raises(ValueError, 'a.flat = [[4, 5, 6, 7, 8], [4, 5, 6]]')
        assert str(exc.value).find("sequence") > 0
        b = a[::-1, :, ::-1]
        b.flat = range(24)
        assert (a.flatten() == [15, 14 ,13, 12, 19, 18, 17, 16, 23, 22,
                                21, 20, 3, 2, 1, 0, 7, 6, 5, 4,
                                11, 10, 9, 8]).all()
        c = array(['abc'] * 10).reshape(2, 5)
        c.flat = ['defgh', 'ijklmnop']
        assert (c.flatten() == ['def', 'ijk']*5).all()

    def test_slice_copy(self):
        from numpypy import zeros
        a = zeros((10, 10))
        b = a[0].copy()
        assert (b == zeros(10)).all()

    def test_array_interface(self):
        from numpypy import array
        a = array([1, 2, 3])
        i = a.__array_interface__
        assert isinstance(i['data'][0], int)
        assert i['shape'] == (3,)
        assert i['strides'] == None  # Because array is in C order
        assert i['typestr'] == a.dtype.str
        a = a[::2]
        i = a.__array_interface__
        assert isinstance(i['data'][0], int)
        b = array(range(9), dtype=int)
        c = b[3:5]
        b_data = b.__array_interface__['data'][0]
        c_data = c.__array_interface__['data'][0]
        assert b_data + 3 * b.dtype.itemsize == c_data

    def test_array_indexing_one_elem(self):
        from numpypy import array, arange
        raises(IndexError, 'arange(3)[array([3.5])]')
        a = arange(3)[array([1])]
        assert a == 1
        assert a[0] == 1
        raises(IndexError,'arange(3)[array([15])]')
        assert arange(3)[array([-3])] == 0
        raises(IndexError,'arange(3)[array([-15])]')
        assert arange(3)[array(1)] == 1

    def test_fill(self):
        from numpypy import array
        a = array([1, 2, 3])
        a.fill(10)
        assert (a == [10, 10, 10]).all()
        a.fill(False)
        assert (a == [0, 0, 0]).all()
        b = a[:1]
        b.fill(4)
        assert (b == [4]).all()
        assert (a == [4, 0, 0]).all()

        c = b + b
        c.fill(27)
        assert (c == [27]).all()

        d = array(10)
        d.fill(100)
        assert d == 100

        e = array(10, dtype=complex)
        e.fill(1.5-3j)
        assert e == 1.5-3j

    def test_array_indexing_bool(self):
        from numpypy import arange
        a = arange(10)
        assert (a[a > 3] == [4, 5, 6, 7, 8, 9]).all()
        a = arange(10).reshape(5, 2)
        assert (a[a > 3] == [4, 5, 6, 7, 8, 9]).all()
        assert (a[a & 1 == 1] == [1, 3, 5, 7, 9]).all()

    def test_array_indexing_bool_setitem(self):
        from numpypy import arange, array
        a = arange(6)
        a[a > 3] = 15
        assert (a == [0, 1, 2, 3, 15, 15]).all()
        a = arange(6).reshape(3, 2)
        a[a & 1 == 1] = array([8, 9, 10])
        assert (a == [[0, 8], [2, 9], [4, 10]]).all()

    def test_array_indexing_bool_setitem_multidim(self):
        from numpypy import arange
        a = arange(10).reshape(5, 2)
        a[a & 1 == 0] = 15
        assert (a == [[15, 1], [15, 3], [15, 5], [15, 7], [15, 9]]).all()

    def test_array_indexing_bool_setitem_2(self):
        from numpypy import arange
        a = arange(10).reshape(5, 2)
        a = a[::2]
        a[a & 1 == 0] = 15
        assert (a == [[15, 1], [15, 5], [15, 9]]).all()

    def test_array_indexing_bool_specialcases(self):
        from numpypy import arange, array
        a = arange(6)
        exc = raises(ValueError, 'a[a < 3] = [1, 2]')
        assert exc.value[0].find('cannot assign') >= 0
        b = arange(4).reshape(2, 2) + 10
        a[a < 4] = b
        assert (a == [10, 11, 12, 13, 4, 5]).all()
        b += 10
        c = arange(8).reshape(2, 2, 2)
        a[a > 9] = c[:, :, 1]
        assert (c[:, :, 1] == [[1, 3], [5, 7]]).all()
        assert (a == [1, 3, 5, 7, 4, 5]).all()
        a = arange(6)
        a[a > 3] = array([15])
        assert (a == [0, 1, 2, 3, 15, 15]).all()
        a = arange(6).reshape(3, 2)
        exc = raises(ValueError, 'a[a & 1 == 1] = []')
        assert exc.value[0].find('cannot assign') >= 0
        assert (a == [[0, 1], [2, 3], [4, 5]]).all()

    def test_nonarray_assignment(self):
        import numpypy as np
        a = np.arange(10)
        b = np.ones(10, dtype=bool)
        r = np.arange(10)
        def assign(a, b, c):
            a[b] = c
        raises(ValueError, assign, a, b, np.nan)
        #raises(ValueError, assign, a, r, np.nan)  # XXX
        import sys
        if '__pypy__' not in sys.builtin_module_names:
            a[b] = np.array(np.nan)
            #a[r] = np.array(np.nan)
        else:
            raises(ValueError, assign, a, b, np.array(np.nan))
            #raises(ValueError, assign, a, r, np.array(np.nan))

    def test_copy_kwarg(self):
        from numpypy import array
        x = array([1, 2, 3])
        assert (array(x) == x).all()
        assert array(x) is not x
        assert array(x, copy=False) is x
        assert array(x, copy=True) is not x

    def test_ravel(self):
        from numpypy import arange
        assert (arange(3).ravel() == arange(3)).all()
        assert (arange(6).reshape(2, 3).ravel() == arange(6)).all()
        assert (arange(6).reshape(2, 3).T.ravel() == [0, 3, 1, 4, 2, 5]).all()

    def test_nonzero(self):
        from numpypy import array
        nz = array(0).nonzero()
        assert nz[0].size == 0

        nz = array(2).nonzero()
        assert (nz[0] == [0]).all()

        nz = array([1, 0, 3]).nonzero()
        assert (nz[0] == [0, 2]).all()

        nz = array([[1, 0, 3], [2, 0, 4]]).nonzero()
        assert (nz[0] == [0, 0, 1, 1]).all()
        assert (nz[1] == [0, 2, 0, 2]).all()

    def test_take(self):
        from numpypy import arange
        assert (arange(10).take([1, 2, 1, 1]) == [1, 2, 1, 1]).all()
        raises(IndexError, "arange(3).take([15])")
        a = arange(6).reshape(2, 3)
        assert (a.take([1, 0, 3]) == [1, 0, 3]).all()
        assert ((a + a).take([3]) == [6]).all()
        a = arange(12).reshape(2, 6)
        assert (a[:,::2].take([3, 2, 1]) == [6, 4, 2]).all()

    def test_ptp(self):
        import numpypy as np
        x = np.arange(4).reshape((2,2))
        assert x.ptp() == 3
        assert (x.ptp(axis=0) == [2, 2]).all()
        assert (x.ptp(axis=1) == [1, 1]).all()

    def test_compress(self):
        from numpypy import arange, array
        a = arange(10)
        assert (a.compress([True, False, True]) == [0, 2]).all()
        assert (a.compress([1, 0, 13]) == [0, 2]).all()
        assert (a.compress([1, 0, 13]) == [0, 2]).all()
        assert (a.compress([1, 0, 13.5]) == [0, 2]).all()
        assert (a.compress(array([1, 0, 13.5], dtype='>f4')) == [0, 2]).all()
        assert (a.compress(array([1, 0, 13.5], dtype='<f4')) == [0, 2]).all()
        assert (a.compress([1, -0-0j, 1.3+13.5j]) == [0, 2]).all()
        a = arange(10).reshape(2, 5)
        assert (a.compress([True, False, True]) == [0, 2]).all()
        raises((IndexError, ValueError), "a.compress([1] * 100)")

    def test_item(self):
        from numpypy import array
        assert array(3).item() == 3
        assert type(array(3).item()) is int
        assert type(array(True).item()) is bool
        assert type(array(3.5).item()) is float
        raises(IndexError, "array(3).item(15)")
        raises(ValueError, "array([1, 2, 3]).item()")
        assert array([3]).item(0) == 3
        assert type(array([3]).item(0)) is int
        assert array([1, 2, 3]).item(-1) == 3
        a = array([1, 2, 3])
        assert a[::2].item(1) == 3
        assert (a + a).item(1) == 4
        raises(IndexError, "array(5).item(1)")
        assert array([1]).item() == 1
        a = array('x')
        assert a.item() == 'x'

    def test_int_array_index(self):
        from numpypy import array
        assert (array([])[[]] == []).all()
        a = array([[1, 2], [3, 4], [5, 6]])
        assert (a[slice(0, 3), [0, 0]] == [[1, 1], [3, 3], [5, 5]]).all()
        assert (a[array([0, 2]), slice(0, 2)] == [[1, 2], [5, 6]]).all()
        b = a[array([0, 0])]
        assert (b == [[1, 2], [1, 2]]).all()
        assert (a[[[0, 1], [0, 0]]] == array([1, 3])).all()
        assert (a[array([0, 2])] == [[1, 2], [5, 6]]).all()
        assert (a[array([0, 2]), 1] == [2, 6]).all()
        assert (a[array([0, 2]), array([1])] == [2, 6]).all()

    def test_int_array_index_setitem(self):
        from numpypy import array
        a = array([[1, 2], [3, 4], [5, 6]])
        a[slice(0, 3), [0, 0]] = [[0, 0], [0, 0], [0, 0]]
        assert (a == [[0, 2], [0, 4], [0, 6]]).all()
        a = array([[1, 2], [3, 4], [5, 6]])
        a[array([0, 2]), slice(0, 2)] = [[10, 11], [12, 13]]
        assert (a == [[10, 11], [3, 4], [12, 13]]).all()

    def test_slice_vector_index(self):
        from numpypy import arange
        b = arange(145)
        a = b[slice(25, 125, None)]
        assert (a == range(25, 125)).all()
        a = b[[slice(25, 125, None)]]
        assert a.shape == (100,)
        # a is a view into b
        a[10] = 200
        assert b[35] == 200
        b[[slice(25, 30)]] = range(5)
        assert all(a[:5] == range(5))
        raises(TypeError, 'b[[[slice(25, 125)]]]')

    def test_cumsum(self):
        from numpypy import arange
        a = arange(6).reshape(3, 2)
        b = arange(6)
        assert (a.cumsum() == [0, 1, 3, 6, 10, 15]).all()
        a.cumsum(out=b)
        assert (b == [0, 1, 3, 6, 10, 15]).all()
        raises(ValueError, "a.cumsum(out=arange(6).reshape(3, 2))")

    def test_cumprod(self):
        from numpypy import array
        a = array([[1, 2], [3, 4], [5, 6]])
        assert (a.cumprod() == [1, 2, 6, 24, 120, 720]).all()

    def test_cumsum_axis(self):
        from numpypy import arange, array
        a = arange(6).reshape(3, 2)
        assert (a.cumsum(0) == [[0, 1], [2, 4], [6, 9]]).all()
        assert (a.cumsum(1) == [[0, 1], [2, 5], [4, 9]]).all()
        a = array([[1, 1], [2, 2], [3, 4]])
        assert (a.cumsum(1) == [[1, 2], [2, 4], [3, 7]]).all()
        assert (a.cumsum(0) == [[1, 1], [3, 3], [6, 7]]).all()

    def test_diagonal(self):
        from numpypy import array
        a = array([[1, 2], [3, 4], [5, 6]])
        raises(ValueError, 'array([1, 2]).diagonal()')
        raises(ValueError, 'a.diagonal(0, 0, 0)')
        raises(ValueError, 'a.diagonal(0, 0, 13)')
        assert (a.diagonal() == [1, 4]).all()
        assert (a.diagonal(1) == [2]).all()

    def test_diagonal_axis(self):
        from numpypy import arange
        a = arange(12).reshape(2, 3, 2)
        assert (a.diagonal(0, 0, 1) == [[0, 8], [1, 9]]).all()
        assert a.diagonal(3, 0, 1).shape == (2, 0)
        assert (a.diagonal(1, 0, 1) == [[2, 10], [3, 11]]).all()
        assert (a.diagonal(0, 2, 1) == [[0, 3], [6, 9]]).all()
        assert (a.diagonal(2, 2, 1) == [[4], [10]]).all()
        assert (a.diagonal(1, 2, 1) == [[2, 5], [8, 11]]).all()

    def test_diagonal_axis_neg_ofs(self):
        from numpypy import arange
        a = arange(12).reshape(2, 3, 2)
        assert (a.diagonal(-1, 0, 1) == [[6], [7]]).all()
        assert a.diagonal(-2, 0, 1).shape == (2, 0)


class AppTestSupport(BaseNumpyAppTest):
    def setup_class(cls):
        import struct
        BaseNumpyAppTest.setup_class.im_func(cls)
        cls.w_data = cls.space.wrap(struct.pack('dddd', 1, 2, 3, 4))
        cls.w_fdata = cls.space.wrap(struct.pack('f', 2.3))
        cls.w_float16val = cls.space.wrap('\x00E') # 5.0 in float16
        cls.w_float32val = cls.space.wrap(struct.pack('f', 5.2))
        cls.w_float64val = cls.space.wrap(struct.pack('d', 300.4))
        cls.w_ulongval = cls.space.wrap(struct.pack('L', 12))

    def test_fromstring(self):
        import sys
        from numpypy import fromstring, dtype

        a = fromstring(self.data)
        for i in range(4):
            assert a[i] == i + 1
        b = fromstring('\x01\x02', dtype='uint8')
        assert a[0] == 1
        assert a[1] == 2
        c = fromstring(self.fdata, dtype='float32')
        assert c[0] == dtype('float32').type(2.3)
        d = fromstring("1 2", sep=' ', count=2, dtype='uint8')
        assert len(d) == 2
        assert d[0] == 1
        assert d[1] == 2
        e = fromstring('3, 4,5', dtype='uint8', sep=',')
        assert len(e) == 3
        assert e[0] == 3
        assert e[1] == 4
        assert e[2] == 5
        f = fromstring('\x01\x02\x03\x04\x05', dtype='uint8', count=3)
        assert len(f) == 3
        assert f[0] == 1
        assert f[1] == 2
        assert f[2] == 3
        g = fromstring("1  2    3 ", dtype='uint8', sep=" ")
        assert len(g) == 3
        assert g[0] == 1
        assert g[1] == 2
        assert g[2] == 3
        h = fromstring("1, , 2, 3", dtype='uint8', sep=",")
        assert (h == [1, 0, 2, 3]).all()
        i = fromstring("1    2 3", dtype='uint8', sep=" ")
        assert (i == [1, 2, 3]).all()
        j = fromstring("1\t\t\t\t2\t3", dtype='uint8', sep="\t")
        assert (j == [1, 2, 3]).all()
        k = fromstring("1,x,2,3", dtype='uint8', sep=",")
        assert (k == [1, 0]).all()
        l = fromstring("1,x,2,3", dtype='float32', sep=",")
        assert (l == [1.0, -1.0]).all()
        m = fromstring("1,,2,3", sep=",")
        assert (m == [1.0, -1.0, 2.0, 3.0]).all()
        n = fromstring("3.4 2.0 3.8 2.2", dtype='int32', sep=" ")
        assert (n == [3]).all()
        o = fromstring("1.0 2f.0f 3.8 2.2", dtype='float32', sep=" ")
        assert len(o) == 2
        assert o[0] == 1.0
        assert o[1] == 2.0
        p = fromstring("1.0,,2.0,3.0", sep=",")
        assert (p == [1.0, -1.0, 2.0, 3.0]).all()
        q = fromstring("1.0,,2.0,3.0", sep=" ")
        assert (q == [1.0]).all()
        r = fromstring("\x01\x00\x02", dtype='bool')
        assert (r == [True, False, True]).all()
        s = fromstring("1,2,3,,5", dtype=bool, sep=",")
        assert (s == [True, True, True, True, True]).all()
        t = fromstring("", bool)
        assert (t == []).all()
        u = fromstring("\x01\x00\x00\x00\x00\x00\x00\x00", dtype=int)
        if sys.maxint > 2 ** 31 - 1:
            assert (u == [1]).all()
        else:
            assert (u == [1, 0]).all()

    def test_fromstring_types(self):
        from numpypy import fromstring, array, dtype
        a = fromstring('\xFF', dtype='int8')
        assert a[0] == -1
        b = fromstring('\xFF', dtype='uint8')
        assert b[0] == 255
        c = fromstring('\xFF\xFF', dtype='int16')
        assert c[0] == -1
        d = fromstring('\xFF\xFF', dtype='uint16')
        assert d[0] == 65535
        e = fromstring('\xFF\xFF\xFF\xFF', dtype='int32')
        assert e[0] == -1
        f = fromstring('\xFF\xFF\xFF\xFF', dtype='uint32')
        assert repr(f[0]) == '4294967295'
        g = fromstring('\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF', dtype='int64')
        assert g[0] == -1
        h = fromstring(self.float32val, dtype='float32')
        assert h[0] == dtype('float32').type(5.2)
        i = fromstring(self.float64val, dtype='float64')
        assert i[0] == dtype('float64').type(300.4)
        j = fromstring(self.ulongval, dtype='L')
        assert j[0] == 12
        k = fromstring(self.float16val, dtype='float16')
        assert k[0] == dtype('float16').type(5.)
        dt =  array([5],dtype='longfloat').dtype
        if dt.itemsize == 12:
            m = fromstring('\x00\x00\x00\x00\x00\x00\x00\xa0\x01@\x00\x00', dtype='float96')
        elif dt.itemsize == 16:
            m = fromstring('\x00\x00\x00\x00\x00\x00\x00\xa0\x01@\x00\x00\x00\x00\x00\x00', dtype='float128')
        elif dt.itemsize == 8:
            skip('longfloat is float64')
        else:
            skip('unknown itemsize for longfloat')
        assert m[0] == dtype('longfloat').type(5.)

    def test_fromstring_invalid(self):
        from numpypy import fromstring
        #default dtype is 64-bit float, so 3 bytes should fail
        raises(ValueError, fromstring, "\x01\x02\x03")
        #3 bytes is not modulo 2 bytes (int16)
        raises(ValueError, fromstring, "\x01\x03\x03", dtype='uint16')
        #5 bytes is larger than 3 bytes
        raises(ValueError, fromstring, "\x01\x02\x03", count=5, dtype='uint8')

    def test_tostring(self):
        from numpypy import array
        assert array([1, 2, 3], 'i2').tostring() == '\x01\x00\x02\x00\x03\x00'
        assert array([1, 2, 3], 'i2')[::2].tostring() == '\x01\x00\x03\x00'
        assert array([1, 2, 3], '<i2')[::2].tostring() == '\x01\x00\x03\x00'
        assert array([1, 2, 3], '>i2')[::2].tostring() == '\x00\x01\x00\x03'
        assert array(0, dtype='i2').tostring() == '\x00\x00'


class AppTestRepr(BaseNumpyAppTest):
    def setup_class(cls):
        if option.runappdirect:
            py.test.skip("Can't be run directly.")
        BaseNumpyAppTest.setup_class.im_func(cls)
        cache = get_appbridge_cache(cls.space)
        cls.old_array_repr = cache.w_array_repr
        cls.old_array_str = cache.w_array_str
        cache.w_array_str = None
        cache.w_array_repr = None

    def test_repr_str(self):
        from numpypy import array
        assert repr(array([1, 2, 3])) == 'array([1, 2, 3])'
        assert str(array([1, 2, 3])) == 'array([1, 2, 3])'
        assert repr(array(['abc'], 'S3')) == "array(['abc'])"
        assert str(array(['abc'], 'S3')) == "array(['abc'])"

    def teardown_class(cls):
        if option.runappdirect:
            return
        cache = get_appbridge_cache(cls.space)
        cache.w_array_repr = cls.old_array_repr
        cache.w_array_str = cls.old_array_str


class AppTestRecordDtype(BaseNumpyAppTest):
    spaceconfig = dict(usemodules=["micronumpy", "struct", "binascii"])

    def test_zeros(self):
        from numpypy import zeros
        a = zeros(2, dtype=[('x', int), ('y', float)])
        raises(IndexError, 'a[0]["xyz"]')
        assert a[0]['x'] == 0
        assert a[0]['y'] == 0
        raises(ValueError, "a[0] = (1, 2, 3)")
        a[0]['x'] = 13
        assert a[0]['x'] == 13
        a[1] = (1, 2)
        assert a[1]['y'] == 2
        b = zeros(2, dtype=[('x', int), ('y', float)])
        b[1] = a[1]
        assert a[1]['y'] == 2

    def test_views(self):
        from numpypy import array
        a = array([(1, 2), (3, 4)], dtype=[('x', int), ('y', float)])
        raises((IndexError, ValueError), 'array([1])["x"]')
        raises((IndexError, ValueError), 'a["z"]')
        assert a['x'][1] == 3
        assert a['y'][1] == 4
        a['x'][0] = 15
        assert a['x'][0] == 15
        b = a['x'] + a['y']
        assert (b == [15+2, 3+4]).all()
        assert b.dtype == float

    def test_assign_tuple(self):
        from numpypy import zeros
        a = zeros((2, 3), dtype=[('x', int), ('y', float)])
        a[1, 2] = (1, 2)
        assert a['x'][1, 2] == 1
        assert a['y'][1, 2] == 2

    def test_creation_and_repr(self):
        from numpypy import array
        a = array([(1, 2), (3, 4)], dtype=[('x', int), ('y', float)])
        assert repr(a[0]) == '(1, 2.0)'

    def test_nested_dtype(self):
        from numpypy import zeros
        a = [('x', int), ('y', float)]
        b = [('x', int), ('y', a)]
        arr = zeros(3, dtype=b)
        arr[1]['x'] = 15
        assert arr[1]['x'] == 15
        arr[1]['y']['y'] = 3.5
        assert arr[1]['y']['y'] == 3.5
        assert arr[1]['y']['x'] == 0.0
        assert arr[1]['x'] == 15

    def test_string_record(self):
        from numpypy import dtype, array

        d = dtype([('x', str), ('y', 'int32')])
        assert str(d.fields['x'][0]) == '|S0'
        assert d.fields['x'][1] == 0
        assert str(d.fields['y'][0]) == 'int32'
        assert d.fields['y'][1] == 0
        assert d.name == 'void32'

        a = array([('a', 2), ('cde', 1)], dtype=d)
        if 0: # XXX why does numpy allow this?
            assert a[0]['x'] == '\x02'
        assert a[0]['y'] == 2
        if 0: # XXX why does numpy allow this?
            assert a[1]['x'] == '\x01'
        assert a[1]['y'] == 1

        d = dtype([('x', 'S1'), ('y', 'int32')])
        assert str(d.fields['x'][0]) == '|S1'
        assert d.fields['x'][1] == 0
        assert str(d.fields['y'][0]) == 'int32'
        assert d.fields['y'][1] == 1
        assert d.name == 'void40'

        a = array([('a', 2), ('cde', 1)], dtype=d)
        assert a[0]['x'] == 'a'
        assert a[0]['y'] == 2
        assert a[1]['x'] == 'c'
        assert a[1]['y'] == 1

    def test_string_array(self):
        from numpypy import array
        a = array(['abc'])
        assert str(a.dtype) == '|S3'
        a = array(['abc'], 'S')
        assert str(a.dtype) == '|S3'
        a = array(['abc'], 'S3')
        assert str(a.dtype) == '|S3'
        a = array(['abcde'], 'S3')
        assert str(a.dtype) == '|S3'
        a = array(['abc', 'defg', 'ab'])
        assert str(a.dtype) == '|S4'
        assert a[0] == 'abc'
        assert a[1] == 'defg'
        assert a[2] == 'ab'
        a = array(['abc', 'defg', 'ab'], 'S3')
        assert str(a.dtype) == '|S3'
        assert a[0] == 'abc'
        assert a[1] == 'def'
        assert a[2] == 'ab'
        raises(TypeError, a, 'sum')
        raises(TypeError, 'a+a')
        b = array(['abcdefg', 'ab', 'cd'])
        assert a[2] == b[1]
        assert bool(a[1])
        c = array(['ab','cdefg','hi','jk'])
        # not implemented yet
        #c[0] += c[3]
        #assert c[0] == 'abjk'

    def test_to_str(self):
        from numpypy import array
        a = array(['abc','abc', 'def', 'ab'], 'S3')
        b = array(['mnopqr','abcdef', 'ab', 'cd'])
        assert b[1] != a[1]

    def test_string_scalar(self):
        from numpypy import array
        a = array('ffff')
        assert a.shape == ()
        a = array([], dtype='S')
        assert str(a.dtype) == '|S1'
        a = array('x', dtype='>S')
        assert str(a.dtype) == '|S1'
        a = array('x', dtype='c')
        assert str(a.dtype) == '|S1'
        assert a == 'x'

    def test_pickle(self):
        from numpypy import dtype, array
        from cPickle import loads, dumps

        d = dtype([('x', str), ('y', 'int32')])
        a = array([('a', 2), ('cde', 1)], dtype=d)

        a = loads(dumps(a))
        d = a.dtype

        assert str(d.fields['x'][0]) == '|S0'
        assert d.fields['x'][1] == 0
        assert str(d.fields['y'][0]) == 'int32'
        assert d.fields['y'][1] == 0
        assert d.name == 'void32'

        assert a[0]['y'] == 2
        assert a[1]['y'] == 1

    def test_subarrays(self):
        from numpypy import dtype, array, zeros

        d = dtype([("x", "int", 3), ("y", "float", 5)])
        a = array([([1, 2, 3], [0.5, 1.5, 2.5, 3.5, 4.5]), ([4, 5, 6], [5.5, 6.5, 7.5, 8.5, 9.5])], dtype=d)

        for v in ['x', u'x', 0, -2]:
            assert (a[0][v] == [1, 2, 3]).all()
            assert (a[1][v] == [4, 5, 6]).all()
        for v in ['y', u'y', -1, 1]:
            assert (a[0][v] == [0.5, 1.5, 2.5, 3.5, 4.5]).all()
            assert (a[1][v] == [5.5, 6.5, 7.5, 8.5, 9.5]).all()
        for v in [-3, 2]:
            exc = raises(IndexError, "a[0][%d]" % v)
            assert exc.value.message == "invalid index (%d)" % (v + 2 if v < 0 else v)
        exc = raises(IndexError, "a[0]['z']")
        assert exc.value.message == "invalid index"
        exc = raises(IndexError, "a[0][None]")
        assert exc.value.message == "invalid index"

        exc = raises(IndexError, "a[0][None]")
        assert exc.value.message == 'invalid index'

        a[0]["x"][0] = 200
        assert a[0]["x"][0] == 200

        d = dtype([("x", "int64", (2, 3))])
        a = array([([[1, 2, 3], [4, 5, 6]],)], dtype=d)

        assert a[0]["x"].dtype == dtype("int64")
        assert a[0]["x"][0].dtype == dtype("int64")

        assert (a[0]["x"][0] == [1, 2, 3]).all()
        assert (a[0]["x"] == [[1, 2, 3], [4, 5, 6]]).all()

        d = dtype((float, (10, 10)))
        a = zeros((3,3), dtype=d)
        assert a[0, 0].shape == (10, 10)
        assert a.shape == (3, 3, 10, 10)
        a[0, 0] = 500
        assert (a[0, 0, 0] == 500).all()
        assert a[0, 0, 0].shape == (10,)
        exc = raises(ValueError, "a[0, 0]['z']")
        assert exc.value.message == 'field named z not found'

    def test_subarray_multiple_rows(self):
        import numpypy as np
        descr = [
            ('x', 'i4', (2,)),
            ('y', 'f8', (2, 2)),
            ('z', 'u1')]
        buf = [
            # x     y                  z
            ([3,2], [[6.,4.],[6.,4.]], 8),
            ([4,3], [[7.,5.],[7.,5.]], 9),
            ]
        h = np.array(buf, dtype=descr)
        assert len(h) == 2
        skip('broken')  # XXX
        assert np.array_equal(h['x'], np.array([buf[0][0],
                                                buf[1][0]], dtype='i4'))
        assert np.array_equal(h['y'], np.array([buf[0][1],
                                                buf[1][1]], dtype='f8'))
        assert np.array_equal(h['z'], np.array([buf[0][2],
                                                buf[1][2]], dtype='u1'))

    def test_multidim_subarray(self):
        from numpypy import dtype, array

        d = dtype([("x", "int64", (2, 3))])
        a = array([([[1, 2, 3], [4, 5, 6]],)], dtype=d)

        assert a[0]["x"].dtype == dtype("int64")
        assert a[0]["x"][0].dtype == dtype("int64")

        assert (a[0]["x"][0] == [1, 2, 3]).all()
        assert (a[0]["x"] == [[1, 2, 3], [4, 5, 6]]).all()

    def test_list_record(self):
        from numpypy import dtype, array

        d = dtype([("x", "int", 3), ("y", "float", 5)])
        a = array([([1, 2, 3], [0.5, 1.5, 2.5, 3.5, 4.5]), ([4, 5, 6], [5.5, 6.5, 7.5, 8.5, 9.5])], dtype=d)

        assert len(list(a[0])) == 2

    def test_issue_1589(self):
        import numpypy as numpy
        c = numpy.array([[(1, 2, 'a'), (3, 4, 'b')], [(5, 6, 'c'), (7, 8, 'd')]],
                        dtype=[('bg', 'i8'), ('fg', 'i8'), ('char', 'S1')])
        assert c[0][0]["char"] == 'a'

    def test_scalar_coercion(self):
        import numpypy as np
        a = np.array([1,2,3], dtype='int16')
        assert (a * 2).dtype == np.dtype('int16')

class AppTestPyPy(BaseNumpyAppTest):
    def setup_class(cls):
        if option.runappdirect and '__pypy__' not in sys.builtin_module_names:
            py.test.skip("pypy only test")
        BaseNumpyAppTest.setup_class.im_func(cls)

    def test_init_2(self):
        # this test is pypy only since in numpy it becomes an object dtype
        import numpypy
        raises(ValueError, numpypy.array, [[1], 2])
        raises(ValueError, numpypy.array, [[1, 2], [3]])
        raises(ValueError, numpypy.array, [[[1, 2], [3, 4], 5]])
        raises(ValueError, numpypy.array, [[[1, 2], [3, 4], [5]]])
        a = numpypy.array([[1, 2], [4, 5]])
        assert a[0, 1] == 2
        assert a[0][1] == 2
        a = numpypy.array(([[[1, 2], [3, 4], [5, 6]]]))
        assert (a[0, 1] == [3, 4]).all()

    def test_from_shape_and_storage(self):
        from numpypy import array, ndarray
        x = array([1, 2, 3, 4])
        addr, _ = x.__array_interface__['data']
        y = ndarray._from_shape_and_storage([2, 2], addr, x.dtype)
        assert y[0, 1] == 2
        y[0, 1] = 42
        assert x[1] == 42
        class C(ndarray):
            pass
        z = ndarray._from_shape_and_storage([4, 1], addr, x.dtype, C)
        assert isinstance(z, C)
        assert z.shape == (4, 1)
        assert z[1, 0] == 42

    def test___pypy_data__(self):
        from numpypy import array
        x = array([1, 2, 3, 4])
        x.__pypy_data__ is None
        obj = object()
        x.__pypy_data__ = obj
        assert x.__pypy_data__ is obj
        del x.__pypy_data__
        assert x.__pypy_data__ is None
