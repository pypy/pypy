import py
from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest


class AppTestSupport(BaseNumpyAppTest):
    def setup_class(cls):
        from numpypy import ndarray
        BaseNumpyAppTest.setup_class.im_func(cls)
        class NoNew(ndarray):
            def __new__(cls):
                raise ValueError('should not call __new__')
            def __array_finalize(self, obj):
                self.called_finalize = True
        class SubType(ndarray):
            def __new__(cls):
                cls.called_new = True
                return cls
            def __array_finalize(self, obj):
                self.called_finalize = True
            cls.w_NoNew = cls.space.wrap(NoNew)
            cls.w_SubType = cls.space.wrap(SubType)

    def test_sub_where(self):
        from numpypy import where, ones, zeros, array
        a = array([1, 2, 3, 0, -3])
        v = a.view(self.NoNew)
        assert False

    def test_repeat(self):
        assert False

    def test_flatiter(self):
        assert False

    def test_getitem_filter(self):
        assert False

    def test_getitem_array_int(self):
        assert False

    def test_round(self):
        from numpypy import array
        a = array(range(10), dtype=float).view(self.NoNew)
        # numpy compatibility
        b = a.round(decimal=0)
        assert isinstance(b, self.NoNew)
        b = a.round(decimal=1)
        assert not isinstance(b, self.NoNew)
        b = a.round(decimal=-1)
        assert not isinstance(b, self.NoNew)

    def test_dot(self):
        # the returned type is that of the first argument
        assert False

    def test_reduce(self):
        # i.e. sum, max
        # test for out as well
        assert False

    def test_call2(self):
        # c + a vs. a + c, what about array priority?
        assert False

    def test_call1(self):
        assert False

    def test_astype(self):
        assert False

    def test_reshape(self):
        assert False
