import py
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin


class ImmutableFieldsTests:

    def test_fields(self):
        class X(object):
            _immutable_fields_ = ["x"]

            def __init__(self, x):
                self.x = x

        def f(x):
            y = X(x)
            return y.x + 5
        res = self.interp_operations(f, [23])
        assert res == 28
        self.check_history_(getfield_gc=0, getfield_gc_pure=1, int_add=1)

    def test_array(self):
        class X(object):
            _immutable_fields_ = ["y[*]"]

            def __init__(self, x):
                self.y = x
        def f(index):
            l = [1, 2, 3, 4]
            l[2] = 30
            a = X(l)
            return a.y[index]
        res = self.interp_operations(f, [2], listops=True)
        assert res == 30
        self.check_history_(getfield_gc=0, getfield_gc_pure=1,
                            getarrayitem_gc=0, getarrayitem_gc_pure=1)


class TestLLtypeImmutableFieldsTests(ImmutableFieldsTests, LLJitMixin):
    pass

# XXX implement
# class TestOOtypeImmutableFieldsTests(ImmutableFieldsTests, OOJitMixin):
#    pass
