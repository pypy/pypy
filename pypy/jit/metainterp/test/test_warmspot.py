import py
from pypy.jit.metainterp.warmspot import ll_meta_interp
from pypy.jit.metainterp.warmspot import get_stats
from pypy.rlib.jit import JitDriver, OPTIMIZER_FULL, OPTIMIZER_SIMPLE
from pypy.rlib.jit import unroll_safe
from pypy.jit.backend.llgraph import runner

from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin


class Exit(Exception):
    def __init__(self, result):
        self.result = result


class WarmspotTests(object):
    
    def test_basic(self):
        mydriver = JitDriver(reds=['a'],
                             greens=['i'])
        CODE_INCREASE = 0
        CODE_JUMP = 1
        lst = [CODE_INCREASE, CODE_INCREASE, CODE_JUMP]
        def interpreter_loop(a):
            i = 0
            while True:
                mydriver.jit_merge_point(i=i, a=a)
                if i >= len(lst):
                    break
                elem = lst[i]
                if elem == CODE_INCREASE:
                    a = a + 1
                    i += 1
                elif elem == CODE_JUMP:
                    if a < 20:
                        i = 0
                        mydriver.can_enter_jit(i=i, a=a)
                    else:
                        i += 1
                else:
                    pass
            raise Exit(a)

        def main(a):
            try:
                interpreter_loop(a)
            except Exit, e:
                return e.result

        res = self.meta_interp(main, [1])
        assert res == 21

    def test_reentry(self):
        mydriver = JitDriver(reds = ['n'], greens = [])

        def f(n):
            while n > 0:
                mydriver.can_enter_jit(n=n)
                mydriver.jit_merge_point(n=n)
                if n % 20 == 0:
                    n -= 2
                n -= 1

        res = self.meta_interp(f, [60])
        assert res == f(30)

    def test_location(self):
        def get_printable_location(n):
            return 'GREEN IS %d.' % n
        myjitdriver = JitDriver(greens=['n'], reds=['m'],
                                get_printable_location=get_printable_location)
        def f(n, m):
            while m > 0:
                myjitdriver.can_enter_jit(n=n, m=m)
                myjitdriver.jit_merge_point(n=n, m=m)
                m -= 1

        self.meta_interp(f, [123, 10])
        assert len(get_stats().locations) >= 4
        for loc in get_stats().locations:
            assert loc == 'GREEN IS 123.'

    def test_set_param_optimizer(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        class A(object):
            def m(self, n):
                return n-1
            
        def g(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                n = A().m(n)
            return n
        def f(n, optimizer):
            myjitdriver.set_param('optimizer', optimizer)
            return g(n)

        # check that the set_param will override the default
        res = self.meta_interp(f, [10, OPTIMIZER_SIMPLE],
                               optimizer=OPTIMIZER_FULL)
        assert res == 0
        self.check_loops(new_with_vtable=1)

        res = self.meta_interp(f, [10, OPTIMIZER_FULL],
                               optimizer=OPTIMIZER_SIMPLE)
        assert res == 0
        self.check_loops(new_with_vtable=0)

    def test_optimizer_default_choice(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        def f(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                n -= 1
            return n

        from pypy.rpython.test.test_llinterp import gengraph
        t, rtyper, graph = gengraph(f, [int], type_system=self.type_system,
                                    **{'translation.gc': 'boehm'})
        
        from pypy.jit.metainterp.warmspot import WarmRunnerDesc

        warmrunnerdescr = WarmRunnerDesc(t, CPUClass=self.CPUClass,
                                         optimizer=None) # pick default

        from pypy.jit.metainterp import optimize

        assert warmrunnerdescr.state.optimize_loop is optimize.optimize_loop
        assert warmrunnerdescr.state.optimize_bridge is optimize.optimize_bridge

    def test_static_debug_level(self):
        from pypy.rlib.jit import DEBUG_PROFILE, DEBUG_OFF, DEBUG_STEPS
        from pypy.jit.metainterp.jitprof import EmptyProfiler, Profiler
        
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        def f(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                n -= 1
            return n

        outerr = py.io.StdCaptureFD()
        self.meta_interp(f, [10], debug_level=DEBUG_OFF,
                                  ProfilerClass=Profiler)
        out, errf = outerr.done()
        err = errf.read()
        assert not 'ENTER' in err
        assert not 'LEAVE' in err
        assert not "Running asm" in err
        outerr = py.io.StdCaptureFD()
        self.meta_interp(f, [10], debug_level=DEBUG_PROFILE,
                                  ProfilerClass=Profiler)
        out, errf = outerr.done()
        err = errf.read()
        assert not 'ENTER' in err
        assert not 'LEAVE' in err
        assert not 'compiled new' in err
        assert "Running asm" in err
        outerr = py.io.StdCaptureFD()
        self.meta_interp(f, [10], debug_level=DEBUG_STEPS,
                                  ProfilerClass=Profiler)
        out, errf = outerr.done()
        err = errf.read()
        assert 'ENTER' in err
        assert 'LEAVE' in err
        assert "Running asm" in err
        outerr = py.io.StdCaptureFD()
        self.meta_interp(f, [10], debug_level=DEBUG_STEPS,
                                  ProfilerClass=EmptyProfiler)
        out, errf = outerr.done()
        err = errf.read()
        assert 'ENTER' in err
        assert 'LEAVE' in err
        assert not "Running asm" in err

    def test_set_param_debug(self):
        from pypy.rlib.jit import DEBUG_PROFILE, DEBUG_OFF, DEBUG_STEPS
        from pypy.jit.metainterp.jitprof import EmptyProfiler, Profiler
        
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        def f(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                n -= 1
            return n

        def main(n, debug):
            myjitdriver.set_param("debug", debug)
            print f(n)

        outerr = py.io.StdCaptureFD()
        self.meta_interp(main, [10, DEBUG_OFF], debug_level=DEBUG_STEPS,
                                                ProfilerClass=Profiler)
        out, errf = outerr.done()
        err = errf.read()
        assert not 'ENTER' in err
        assert not 'LEAVE' in err
        assert not "Running asm" in err
        outerr = py.io.StdCaptureFD()
        self.meta_interp(main, [10, DEBUG_PROFILE], debug_level=DEBUG_STEPS,
                                                    ProfilerClass=Profiler)
        out, errf = outerr.done()
        err = errf.read()
        assert not 'ENTER' in err
        assert not 'LEAVE' in err
        assert not 'compiled new' in err
        assert "Running asm" in err
        outerr = py.io.StdCaptureFD()
        self.meta_interp(main, [10, DEBUG_STEPS], debug_level=DEBUG_OFF,
                                                  ProfilerClass=Profiler)
        out, errf = outerr.done()
        err = errf.read()
        assert 'ENTER' in err
        assert 'LEAVE' in err
        assert "Running asm" in err

    def test_unwanted_loops(self):
        mydriver = JitDriver(reds = ['n', 'total', 'm'], greens = [])

        def loop1(n):
            # the jit should not look here, as there is a loop
            res = 0
            for i in range(n):
                res += i
            return res

        @unroll_safe
        def loop2(n):
            # the jit looks here, due to the decorator
            for i in range(5):
                n += 1
            return n

        def f(m):
            total = 0
            n = 0
            while n < m:
                mydriver.can_enter_jit(n=n, total=total, m=m)
                mydriver.jit_merge_point(n=n, total=total, m=m)
                total += loop1(n)
                n = loop2(n)
            return total
        self.meta_interp(f, [50])
        self.check_enter_count_at_most(2)

    def test_wanted_unrolling_and_preinlining(self):
        mydriver = JitDriver(reds = ['n', 'm'], greens = [])

        @unroll_safe
        def loop2(n):
            # the jit looks here, due to the decorator
            for i in range(5):
                n += 1
            return n
        loop2._always_inline_ = True

        def g(n):
            return loop2(n)
        g._dont_inline_ = True

        def f(m):
            n = 0
            while n < m:
                mydriver.can_enter_jit(n=n, m=m)
                mydriver.jit_merge_point(n=n, m=m)
                n = g(n)
            return n
        self.meta_interp(f, [50], backendopt=True)
        self.check_enter_count_at_most(2)
        self.check_loops(call=0)


class TestLLWarmspot(WarmspotTests, LLJitMixin):
    CPUClass = runner.LLtypeCPU
    type_system = 'lltype'

class TestOOWarmspot(WarmspotTests, OOJitMixin):
    CPUClass = runner.OOtypeCPU
    type_system = 'ootype'
