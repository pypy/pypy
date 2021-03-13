import py
from rpython.rlib.jit import JitDriver, set_param, Counters
from rpython.rlib.jit import unroll_safe, dont_look_inside, promote
from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.jit.metainterp.warmspot import get_stats
from rpython.jit.metainterp.jitprof import Profiler

class TraceLimitTests:
    def test_segmented_trace(self):
        def p(pc, code):
            return "%s %d %s" % (code, pc, code[pc])
        myjitdriver = JitDriver(greens=['pc', 'code'], reds=['n'],
                                get_printable_location=p,
                                is_recursive=True)

        def f(code, n):
            pc = 0
            while pc < len(code):

                myjitdriver.jit_merge_point(n=n, code=code, pc=pc)
                op = code[pc]
                if op == "-":
                    n -= 1
                elif op == "c":
                    f('--------------------', n)
                elif op == "l":
                    if n > 0:
                        myjitdriver.can_enter_jit(n=n, code=code, pc=0)
                        pc = 0
                        continue
                else:
                    assert 0
                pc += 1
            return n
        def g(m):
            set_param(None, 'inlining', True)
            set_param(None, 'trace_limit', 40)
            if m > 1000000:
                f('', 0)
            result = 0
            s = '-' * 50 + '-c-l-'
            for i in range(m):
                result += f(s, i+100)
        self.meta_interp(g, [10], backendopt=True, ProfilerClass=Profiler)
        stats = get_stats()
        assert stats.metainterp_sd.profiler.counters[
            Counters.ABORT_SEGMENTED_TRACE] == 8
        self.check_trace_count(10)
        self.check_jitcell_token_count(2)

class TestLLtype(TraceLimitTests, LLJitMixin):
    pass
