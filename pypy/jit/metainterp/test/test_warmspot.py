import py
from pypy.jit.metainterp.warmspot import ll_meta_interp, cast_whatever_to_int
from pypy.jit.metainterp.warmspot import get_stats
from pypy.rlib.jit import JitDriver, OPTIMIZER_FULL, OPTIMIZER_SIMPLE
from pypy.jit.backend.llgraph import runner

from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin


def test_translate_cast_whatever_to_int():
    from pypy.rpython.test.test_llinterp import interpret
    from pypy.rpython.lltypesystem import lltype
    def fn(x):
        return cast_whatever_to_int(lltype.typeOf(x), x)
    for type_system in ('lltype', 'ootype'):
        res = interpret(fn, [42], type_system=type_system)
        assert res == 42

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

    def test_hash_collision(self):
        mydriver = JitDriver(reds = ['n'], greens = ['m'])
        def f(n):
            m = 0
            while n > 0:
                mydriver.can_enter_jit(n=n, m=m)
                mydriver.jit_merge_point(n=n, m=m)
                n -= 1
                if not (n % 11):
                    m = (m+n) & 3
            return m
        res = self.meta_interp(f, [110], hash_bits=1)
        assert res == f(110)

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

    def test_set_param_debug(self):
        from pypy.jit.metainterp.jitprof import Profiler, EmptyProfiler
        from pypy.rlib.jit import DEBUG_PROFILE, DEBUG_OFF, DEBUG_STEPS
        
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        def f(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                n -= 1
            return n

        def main(n, debug):
            myjitdriver.set_param_debug(debug)
            print f(n)

        outerr = py.io.StdCaptureFD()
        self.meta_interp(f, [10], debug=DEBUG_OFF)
        out, errf = outerr.done()
        err = errf.read()
        assert not 'ENTER' in err
        assert not 'LEAVE' in err
        assert "Running asm" not in err
        outerr = py.io.StdCaptureFD()
        self.meta_interp(f, [10], debug=DEBUG_PROFILE)
        out, errf = outerr.done()
        err = errf.read()
        assert not 'ENTER' in err
        assert not 'LEAVE' in err
        assert not 'compiled new' in err
        assert "Running asm" in err
        outerr = py.io.StdCaptureFD()
        self.meta_interp(f, [10], debug=DEBUG_STEPS)
        out, errf = outerr.done()
        err = errf.read()
        assert 'ENTER' in err
        assert 'LEAVE' in err
        assert "Running asm" in err

class TestLLWarmspot(WarmspotTests, LLJitMixin):
    CPUClass = runner.LLtypeCPU
    type_system = 'lltype'

class TestOOWarmspot(WarmspotTests, OOJitMixin):
    CPUClass = runner.OOtypeCPU
    type_system = 'ootype'
