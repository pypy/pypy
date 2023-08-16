from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.rlib.jit import JitDriver, warmup_critical_function


class TestGenextensionExceptions(LLJitMixin):
    def test_change_frame(self):
        myjitdriver = JitDriver(greens = [], reds = ['x'])
        @warmup_critical_function
        def f(x):
            myjitdriver.can_enter_jit(x=x)
            myjitdriver.jit_merge_point(x=x)
            return g(x)
        @warmup_critical_function
        def g(y):
            return y * y
        res = self.meta_interp(f, [5])

        assert res == 25

    def test_exception(self):
        myjitdriver = JitDriver(greens = [], reds = ['x'])
        @warmup_critical_function
        def f(x):
            #myjitdriver.can_enter_jit(x=x)
            #myjitdriver.jit_merge_point(x=x)
            try:
                g(True)
            except ValueError:
                x += 5
            else:
                x += 100

            try:
                g(False)
            except ValueError:
                x += 10
            else:
                x += 200

            return x
        @warmup_critical_function
        def g(b):
            if b:
                raise ValueError()
            
        res = self.interp_operations(f, [0])

        assert res == 205