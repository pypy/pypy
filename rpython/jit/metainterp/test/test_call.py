
from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.rlib import jit

class TestCall(LLJitMixin):
    def test_indirect_call(self):
        @jit.dont_look_inside
        def f1(x):
            return x + 1

        @jit.dont_look_inside
        def f2(x):
            return x + 2

        @jit.dont_look_inside
        def choice(i):
            if i:
                return f1
            return f2

        def f(i):
            func = choice(i)
            return func(i)

        res = self.interp_operations(f, [3])
        assert res == f(3)

    def test_call_elidable_none(self):
        d = {}

        @jit.elidable
        def f(a):
            return d.get(a, None)

        driver = jit.JitDriver(greens = [], reds = ['n'])

        def main(n):
            while n > 0:
                driver.jit_merge_point(n=n)
                f(n)
                f(n)
                n -= 1
            return 3

        self.meta_interp(main, [10])

    def test_cond_call(self):
        def f(l, n):
            l.append(n)

        def main(n):
            l = []
            jit.conditional_call(n == 10, f, l, n)
            return len(l)

        assert self.interp_operations(main, [10]) == 1
        assert self.interp_operations(main, [5]) == 0

