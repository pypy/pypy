
from pypy.jit.metainterp.warmspot import ll_meta_interp
from pypy.rlib.jit import JitDriver
from pypy.jit.metainterp.test.test_basic import LLJitMixin
from pypy.jit.metainterp import pyjitpl
from pypy.jit.metainterp.jitprof import *

class FakeProfiler(Profiler):
    def __init__(self):
        self.counter = 0
    
    def timer(self):
        self.counter += 1
        return self.counter - 1

    def print_stats(self):
        pass

class ProfilerMixin(LLJitMixin):
    def meta_interp(self, *args, **kwds):
        kwds = kwds.copy()
        kwds['profile'] = FakeProfiler
        return LLJitMixin.meta_interp(self, *args, **kwds)

class TestProfile(ProfilerMixin):

    def test_simple_loop(self):
        myjitdriver = JitDriver(greens = [], reds = ['x', 'y', 'res'])
        def f(x, y):
            res = 0
            while y > 0:
                myjitdriver.can_enter_jit(x=x, y=y, res=res)
                myjitdriver.jit_merge_point(x=x, y=y, res=res)
                res += x
                y -= 1
            return res * 2
        res = self.meta_interp(f, [6, 7])
        assert res == 84
        profiler = pyjitpl._warmrunnerdesc.metainterp_sd.profiler
        assert len(profiler.events) == 6
        expected = [
            TRACING,
            END_TRACING,
            RUNNING,
            END_RUNNING,
            BLACKHOLE,
            END_BLACKHOLE
            ]
        assert [i[1] for i in profiler.events] == expected
        assert profiler.trace_time == 1
        assert profiler.run_time == 1        
        assert profiler.blackhole_time == 1
