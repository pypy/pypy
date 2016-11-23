
from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.rlib import jit

class CallTest(object):
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

    def test_cond_call(self):
        def f(l, n):
            l.append(n)

        def main(n):
            l = []
            jit.conditional_call(n == 10, f, l, n)
            return len(l)

        assert self.interp_operations(main, [10]) == 1
        assert self.interp_operations(main, [5]) == 0

    def test_cond_call_disappears(self):
        driver = jit.JitDriver(greens = [], reds = ['n'])

        def f(n):
            raise ValueError

        def main(n):
            while n > 0:
                driver.jit_merge_point(n=n)
                jit.conditional_call(False, f, 10)
                n -= 1
            return 42

        assert self.meta_interp(main, [10]) == 42
        self.check_resops(guard_no_exception=0)

    def test_cond_call_i(self):
        @jit.elidable
        def f(n):
            return n * 200

        def main(n, m):
            return jit.conditional_call_value(n, f, m)

        assert self.interp_operations(main, [0, 10]) == 2000
        assert self.interp_operations(main, [15, 42]) == 15

    def test_cond_call_r(self):
        @jit.elidable
        def f(n):
            return [n]

        def main(n):
            if n == 10:
                l = []
            else:
                l = None
            l = jit.conditional_call_value(l, f, n)
            return len(l)

        assert main(10) == 0
        assert main(5) == 1
        assert self.interp_operations(main, [10]) == 0
        assert self.interp_operations(main, [5]) == 1

    def test_cond_call_constant_in_pyjitpl(self):
        @jit.elidable
        def f(a, b):
            return a + b
        def main(n):
            # this is completely constant-folded because the arguments
            # to f() are constants.
            return jit.conditional_call_value(n, f, 40, 2)

        assert main(12) == 12
        assert main(0) == 42
        assert self.interp_operations(main, [12]) == 12
        self.check_operations_history(finish=1)   # empty history
        assert self.interp_operations(main, [0]) == 42
        self.check_operations_history(finish=1)   # empty history

    def test_cond_call_constant_in_optimizer(self):
        myjitdriver = jit.JitDriver(greens = ['m'], reds = ['n', 'p'])
        @jit.elidable
        def externfn(x):
            return x - 3
        class V:
            def __init__(self, value):
                self.value = value
        def f(n, m, p):
            while n > 0:
                myjitdriver.can_enter_jit(n=n, p=p, m=m)
                myjitdriver.jit_merge_point(n=n, p=p, m=m)
                v = V(m)
                n -= jit.conditional_call_value(p, externfn, v.value)
            return n
        res = self.meta_interp(f, [21, 5, 0])
        assert res == -1
        # the COND_CALL_VALUE is constant-folded away by optimizeopt.py
        self.check_resops(call_pure_i=0, cond_call_pure_i=0, call_i=0,
                          int_sub=2)

    def test_cond_call_constant_in_optimizer_2(self):
        myjitdriver = jit.JitDriver(greens = ['m'], reds = ['n', 'p'])
        @jit.elidable
        def externfn(x):
            return 2
        def f(n, m, p):
            while n > 0:
                myjitdriver.can_enter_jit(n=n, p=p, m=m)
                myjitdriver.jit_merge_point(n=n, p=p, m=m)
                assert p > -1
                assert p < 1
                n -= jit.conditional_call_value(p, externfn, n)
            return n
        res = self.meta_interp(f, [21, 5, 0])
        assert res == -1
        # optimizer: the COND_CALL_VALUE is turned into a regular
        # CALL_PURE, which itself becomes a CALL
        self.check_resops(call_pure_i=0, cond_call_pure_i=0, call_i=2,
                          int_sub=2)

    def test_cond_call_constant_in_optimizer_3(self):
        myjitdriver = jit.JitDriver(greens = ['m'], reds = ['n', 'p'])
        @jit.elidable
        def externfn(x):
            return 1
        def f(n, m, p):
            while n > 0:
                myjitdriver.can_enter_jit(n=n, p=p, m=m)
                myjitdriver.jit_merge_point(n=n, p=p, m=m)
                assert p > -1
                assert p < 1
                n0 = n
                n -= jit.conditional_call_value(p, externfn, n0)
                n -= jit.conditional_call_value(p, externfn, n0)
            return n
        res = self.meta_interp(f, [21, 5, 15])
        assert res == -1
        # same as test_cond_call_constant_in_optimizer_2, but the two
        # intermediate CALL_PUREs are replaced with only one, because
        # they are called with the same arguments
        self.check_resops(call_pure_i=0, cond_call_pure_i=0, call_i=2,
                          int_sub=4)

    def test_cond_call_constant_in_optimizer_4(self):
        class X:
            def __init__(self, value):
                self.value = value
                self.triple = 0
            @jit.elidable
            def _compute_triple(self):
                self.triple = self.value * 3
                return self.triple
            def get_triple(self):
                return jit.conditional_call_value(self.triple,
                                                  X._compute_triple, self)
        def main(n):
            x = X(n)
            return x.get_triple() + x.get_triple()

        assert self.interp_operations(main, [100]) == 600
        XXX
        self.check_operations_history(finish=1)   # empty history


class TestCall(LLJitMixin, CallTest):
    pass
