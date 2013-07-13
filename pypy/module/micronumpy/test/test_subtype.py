import py
from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest


class AppTestSupport(BaseNumpyAppTest):
    def setup_class(cls):
        BaseNumpyAppTest.setup_class.im_func(cls)
        cls.w_NoNew = cls.space.appexec([], '''():
            from numpypy import ndarray
            class NoNew(ndarray):
                def __new__(cls, subtype):
                    raise ValueError('should not call __new__')
                def __array_finalize__(self, obj):

                    self.called_finalize = True
            return NoNew ''')
        cls.w_SubType = cls.space.appexec([], '''():
            from numpypy import ndarray, asarray
            class SubType(ndarray):
                def __new__(obj, input_array):
                    obj = asarray(input_array).view(obj)
                    obj.called_new = True
                    return obj
                def __array_finalize__(self, obj):
                    self.called_finalize = True
            return SubType ''')

    def test_subtype_base(self):
        from numpypy import ndarray, dtype
        class C(ndarray):
            def __new__(subtype, shape, dtype):
                self = ndarray.__new__(subtype, shape, dtype)
                self.id = 'subtype'
                return self
        a = C([2, 2], int)
        assert isinstance(a, C)
        assert isinstance(a, ndarray)
        assert a.shape == (2, 2)
        assert a.dtype is dtype(int)
        assert a.id == 'subtype'
        a = a.reshape(1, 4)
        b = a.reshape(4, 1)
        assert isinstance(b, C)
        #make sure __new__ was not called
        assert not getattr(b, 'id', None)
        a.fill(3)
        b = a[0]
        assert isinstance(b, C)
        assert (b == 3).all()
        b[0]=100
        assert a[0,0] == 100

    def test_subtype_view(self):
        from numpypy import ndarray, array
        class matrix(ndarray):
            def __new__(subtype, data, dtype=None, copy=True):
                if isinstance(data, matrix):
                    return data
                return data.view(subtype)
        a = array(range(5))
        b = matrix(a)
        assert isinstance(b, matrix)
        assert (b == a).all()


    def test_finalize(self):
        #taken from http://docs.scipy.org/doc/numpy/user/basics.subclassing.html#simple-example-adding-an-extra-attribute-to-ndarray
        import numpypy as np
        class InfoArray(np.ndarray):
            def __new__(subtype, shape, dtype=float, buffer=None, offset=0,
                          strides=None, order='C', info=None):
                obj = np.ndarray.__new__(subtype, shape, dtype, buffer,
                         offset, strides, order)
                obj.info = info
                return obj

            def __array_finalize__(self, obj):
                if obj is None:
                    print 'finalize with None'
                    return
                # printing the object itself will crash the test
                print 'finalize with something',type(obj)
                self.info = getattr(obj, 'info', None)
        obj = InfoArray(shape=(3,))
        assert isinstance(obj, InfoArray)
        assert obj.info is None
        obj = InfoArray(shape=(3,), info='information')
        assert obj.info == 'information'
        v = obj[1:]
        assert isinstance(v, InfoArray)
        assert v.base is obj
        assert v.info == 'information'
        arr = np.arange(10)
        cast_arr = arr.view(InfoArray)
        assert isinstance(cast_arr, InfoArray)
        assert cast_arr.base is arr
        assert cast_arr.info is None

    def test_sub_where(self):
        from numpypy import where, ones, zeros, array
        a = array([1, 2, 3, 0, -3])
        v = a.view(self.NoNew)
        b = where(array(v) > 0, ones(5), zeros(5))
        assert (b == [1, 1, 1, 0, 0]).all()
        # where returns an ndarray irregardless of the subtype of v
        assert not isinstance(b, self.NoNew)

    def test_sub_repeat(self):
        assert False

    def test_sub_flatiter(self):
        from numpypy import array
        a = array(range(9)).reshape(3, 3).view(self.NoNew)
        c = array(range(9)).reshape(3, 3)
        assert isinstance(a.flat[:] + a.flat[:], self.NoNew)
        assert isinstance(a.flat[:] + c.flat[:], self.NoNew)
        assert isinstance(c.flat[:] + a.flat[:], self.NoNew)
        assert not isinstance(c.flat[:] + c.flat[:], self.NoNew)

    def test_sub_getitem_filter(self):
        assert False

    def test_sub_getitem_array_int(self):
        assert False

    def test_sub_round(self):
        from numpypy import array
        a = array(range(10), dtype=float).view(self.NoNew)
        # numpy compatibility
        b = a.round(decimal=0)
        assert isinstance(b, self.NoNew)
        b = a.round(decimal=1)
        assert not isinstance(b, self.NoNew)
        b = a.round(decimal=-1)
        assert not isinstance(b, self.NoNew)

    def test_sub_dot(self):
        # the returned type is that of the first argument
        assert False

    def test_sub_reduce(self):
        # i.e. sum, max
        # test for out as well
        assert False

    def test_sub_call2(self):
        # c + a vs. a + c, what about array priority?
        from numpypy import array
        a = array(range(12)).view(self.NoNew)
        b = self.SubType(range(12))
        c = b + a
        assert isinstance(c, self.SubType)
        c = a + b
        assert isinstance(c, self.NoNew)

    def test_sub_call1(self):
        from numpypy import array, sqrt
        a = array(range(12)).view(self.NoNew)
        b = sqrt(a)
        assert b.called_finalize == True

    def test_sub_astype(self):
        from numpypy import array
        a = array(range(12)).view(self.NoNew)
        b = a.astype(float)
        assert b.called_finalize == True

    def test_sub_reshape(self):
        from numpypy import array
        a = array(range(12)).view(self.NoNew)
        b = a.reshape(3, 4)
        assert b.called_finalize == True

