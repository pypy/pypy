
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin
from pypy.rlib.jit import JitDriver
from pypy.jit.metainterp.policy import StopAtXPolicy
from pypy.jit.metainterp.warmspot import get_stats
from pypy.jit.metainterp.dump import dump_call_history

class DebugTest:
    def test_callstack(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])

        def x(n):
            pass

        def z(n):
            x(n)

        def g(n):
            z(n)

        def f(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                g(n)
                n -= 1
            return n

        res = self.meta_interp(f, [10], policy=StopAtXPolicy(x))
        assert res == 0
        ch = get_stats().loops[0]._call_history
        cmp = [(i, getattr(j, 'name', None)) for i, j, _ in ch]
        assert cmp == [
            ('enter', 'f'),
            ('enter', 'g'),
            ('enter', 'z'),
            ('call',  None),
            ('leave', 'z'),
            ('leave', 'g'),
            ('guard_failure', None),
            ('enter', 'f'),
            ('leave', 'f'),
            ]
        dump_call_history(ch)

class TestLLtype(DebugTest, LLJitMixin):
    pass

class TestOOtype(DebugTest, OOJitMixin):
    pass
