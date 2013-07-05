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
                def __array_finalize(self, obj):
                    self.called_finalize = True
            return NoNew ''')
        cls.w_SubType = cls.space.appexec([], '''():
            from numpypy import ndarray
            class SubType(ndarray):
                def __new__(cls):
                    cls.called_new = True
                    return cls
                def __array_finalize(self, obj):
                    self.called_finalize = True
            return SubType ''')

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
        print 'a'
        v = obj[1:]
        assert isinstance(v, InfoArray)
        assert v.base is obj
        assert v.info == 'information'
        arr = np.arange(10)
        print '1'
        cast_arr = arr.view(InfoArray)
        assert isinstance(cast_arr, InfoArray)
        assert cast_arr.base is arr
        assert cast_arr.info is None

    def test_sub_where(self):
        from numpypy import where, ones, zeros, array
        a = array([1, 2, 3, 0, -3])
        v = a.view(self.NoNew)
        assert False

    def test_sub_repeat(self):
        assert False

    def test_sub_flatiter(self):
        assert False

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
        assert False

    def test_sub_call1(self):
        assert False

    def test_sub_astype(self):
        assert False

    def test_sub_reshape(self):
        from numpypy import array
        a = array(range(12)).view(self.NoNew)
        b = a.reshape(3, 4)
        assert b.called_finalize == True

