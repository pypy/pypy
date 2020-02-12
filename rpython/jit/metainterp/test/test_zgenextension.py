from rpython.jit.metainterp.test.support import LLJitMixin, noConst
from rpython.rlib.jit import (JitDriver, we_are_jitted, hint, dont_look_inside,
    loop_invariant, elidable, promote, jit_debug, assert_green,
    AssertGreenFailed, unroll_safe, current_trace_length, look_inside_iff,
    isconstant, isvirtual, set_param, record_exact_class,
    warmup_critical_function)

class TestGenExtension(LLJitMixin):
    def test_loop_1(self):
        myjitdriver = JitDriver(greens = [], reds = ['x', 'y', 'res'])
        @warmup_critical_function
        def f(x, y):
            res = 0
            while y > 0:
                myjitdriver.can_enter_jit(x=x, y=y, res=res)
                myjitdriver.jit_merge_point(x=x, y=y, res=res)
                res += x
                y -= 1
            return res
        res = self.meta_interp(f, [6, 7])
        assert res == 42
        self.check_trace_count(1)
        self.check_resops({'jump': 1, 'int_gt': 2, 'int_add': 2,
                           'guard_true': 2, 'int_sub': 2})


    def test_loop_switch(self):
        myjitdriver = JitDriver(greens = [], reds = ['x', 'y', 'res'])
        @warmup_critical_function
        def f(x, y):
            res = 0
            while y > 0:
                myjitdriver.can_enter_jit(x=x, y=y, res=res)
                myjitdriver.jit_merge_point(x=x, y=y, res=res)
                res += x
                if y == 1:
                    res *= 2
                elif y == 2:
                    res += 18
                elif y == 3:
                    res -= 3
                elif y == 3:
                    res -= 3
                elif y == 4:
                    res -= 3
                elif y == 5:
                    res -= 3
                elif y == 6:
                    res -= 3
                elif y == 7:
                    res -= 3
                elif y == 8:
                    res -= 3
                elif y == 9:
                    res -= 3
                elif y == 10:
                    res -= 3
                elif y == 11:
                    res /= 2
                y -= 1
            return res
        res = self.meta_interp(f, [6, 7], backendopt=True)
        assert res == f(6, 7)
