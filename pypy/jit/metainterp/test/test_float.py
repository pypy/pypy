from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin


class FloatTests:

    def test_simple(self):
        def f(a, b, c, d, e):
            return (((a + b) - c) * d) / e
        res = self.interp_operations(f, [41.5, 2.25, 17.5, 3.0, 2.5])
        assert res == 31.5


class TestOOtype(FloatTests, OOJitMixin):
    pass

class TestLLtype(FloatTests, LLJitMixin):
    pass
