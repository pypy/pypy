import py
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin
from pypy.rlib.jit import JitDriver

class DictTests:

    def test_basic_dict(self):
        py.test.skip("in-progress")
        myjitdriver = JitDriver(greens = [], reds = ['n', 'dct'])
        def f(n):
            dct = {}
            while n > 0:
                myjitdriver.can_enter_jit(n=n, dct=dct)
                myjitdriver.jit_merge_point(n=n, dct=dct)
                dct[n] = n*n
                n -= 1
            sum = 0
            for i in dct.values():
                sum += i
            return sum
        assert f(10) == 1 + 4 + 9 + 16 + 25 + 36 + 49 + 64 + 81 + 100
        res = self.meta_interp(f, [10], listops=True)
        assert res == 1 + 4 + 9 + 16 + 25 + 36 + 49 + 64 + 81 + 100


class TestOOtype(DictTests, OOJitMixin):
    def test_basic_dict(self):
        py.test.skip("implement me")

class TestLLtype(DictTests, LLJitMixin):
    pass
