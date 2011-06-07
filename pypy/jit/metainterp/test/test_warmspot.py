import py
from pypy.jit.metainterp.warmspot import ll_meta_interp
from pypy.jit.metainterp.warmspot import get_stats
from pypy.rlib.jit import JitDriver
from pypy.rlib.jit import unroll_safe
from pypy.jit.backend.llgraph import runner
from pypy.jit.metainterp.history import BoxInt

from pypy.jit.metainterp.test.support import LLJitMixin, OOJitMixin
from pypy.jit.metainterp.optimizeopt import ALL_OPTS_NAMES


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
            assert loc == (0, 123)

    def test_set_param_enable_opts(self):
        from pypy.rpython.annlowlevel import llstr, hlstr
        
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
        def f(n, enable_opts):
            myjitdriver.set_param('enable_opts', hlstr(enable_opts))
            return g(n)

        # check that the set_param will override the default
        res = self.meta_interp(f, [10, llstr('')])
        assert res == 0
        self.check_loops(new_with_vtable=1)

        res = self.meta_interp(f, [10, llstr(ALL_OPTS_NAMES)],
                               enable_opts='')
        assert res == 0
        self.check_loops(new_with_vtable=0)

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

    def test_loop_header(self):
        # artificial test: we enter into the JIT only when can_enter_jit()
        # is seen, but we close a loop in the JIT much more quickly
        # because of loop_header().
        mydriver = JitDriver(reds = ['n', 'm'], greens = [])

        def f(m):
            n = 0
            while True:
                mydriver.jit_merge_point(n=n, m=m)
                if n > m:
                    m -= 1
                    if m < 0:
                        return n
                    n = 0
                    mydriver.can_enter_jit(n=n, m=m)
                else:
                    n += 1
                    mydriver.loop_header()
        assert f(15) == 1
        res = self.meta_interp(f, [15], backendopt=True)
        assert res == 1
        self.check_loops(int_add=1)   # I get 13 without the loop_header()

    def test_omit_can_enter_jit(self):
        # Simple test comparing the effects of always giving a can_enter_jit(),
        # or not giving any.  Mostly equivalent, except that if given, it is
        # ignored the first time, and so it ends up taking one extra loop to
        # start JITting.
        mydriver = JitDriver(greens=[], reds=['m'])
        #
        for i2 in range(10):
            def f2(m):
                while m > 0:
                    mydriver.jit_merge_point(m=m)
                    m -= 1
            self.meta_interp(f2, [i2])
            try:
                self.check_tree_loop_count(1)
                break
            except AssertionError:
                print "f2: no loop generated for i2==%d" % i2
        else:
            raise     # re-raise the AssertionError: check_loop_count never 1
        #
        for i1 in range(10):
            def f1(m):
                while m > 0:
                    mydriver.can_enter_jit(m=m)
                    mydriver.jit_merge_point(m=m)
                    m -= 1
            self.meta_interp(f1, [i1])
            try:
                self.check_tree_loop_count(1)
                break
            except AssertionError:
                print "f1: no loop generated for i1==%d" % i1
        else:
            raise     # re-raise the AssertionError: check_loop_count never 1
        #
        assert i1 - 1 == i2

    def test_no_loop_at_all(self):
        mydriver = JitDriver(greens=[], reds=['m'])
        def f2(m):
            mydriver.jit_merge_point(m=m)
            return m - 1
        def f1(m):
            while m > 0:
                m = f2(m)
        self.meta_interp(f1, [8])
        # it should generate one "loop" only, which ends in a FINISH
        # corresponding to the return from f2.
        self.check_tree_loop_count(1)
        self.check_loop_count(0)

    def test_simple_loop(self):
        mydriver = JitDriver(greens=[], reds=['m'])
        def f1(m):
            while m > 0:
                mydriver.jit_merge_point(m=m)
                m = m - 1
        self.meta_interp(f1, [8])
        self.check_loop_count(1)
        self.check_loops({'int_sub': 1, 'int_gt': 1, 'guard_true': 1,
                          'jump': 1})


class TestLLWarmspot(WarmspotTests, LLJitMixin):
    CPUClass = runner.LLtypeCPU
    type_system = 'lltype'

class TestOOWarmspot(WarmspotTests, OOJitMixin):
    ##CPUClass = runner.OOtypeCPU
    type_system = 'ootype'

class TestWarmspotDirect(object):
    def setup_class(cls):
        from pypy.jit.metainterp.typesystem import llhelper
        from pypy.jit.codewriter.support import annotate
        from pypy.jit.metainterp.warmspot import WarmRunnerDesc
        from pypy.rpython.lltypesystem.rclass import OBJECT, OBJECT_VTABLE
        from pypy.rpython.lltypesystem import lltype, llmemory
        exc_vtable = lltype.malloc(OBJECT_VTABLE, immortal=True)
        cls.exc_vtable = exc_vtable

        class FakeLoopToken:
            def __init__(self, no):
                self.no = no
                self.generation = 0

        class FakeFailDescr(object):
            def __init__(self, looptoken):
                assert isinstance(looptoken, FakeLoopToken)
                self.looptoken = looptoken
            
            def handle_fail(self, metainterp_sd, jitdrivers_sd):
                no = self.looptoken.no
                if no == 0:
                    raise metainterp_sd.warmrunnerdesc.DoneWithThisFrameInt(3)
                if no == 1:
                    raise metainterp_sd.warmrunnerdesc.ContinueRunningNormally(
                        [0], [], [], [1], [], [])
                if no == 3:
                    exc = lltype.malloc(OBJECT)
                    exc.typeptr = exc_vtable
                    raise metainterp_sd.warmrunnerdesc.ExitFrameWithExceptionRef(
                        metainterp_sd.cpu,
                        lltype.cast_opaque_ptr(llmemory.GCREF, exc))
                return self.looptoken

        class FakeDescr:
            def as_vtable_size_descr(self):
                return self

        class FakeCPU(object):
            supports_floats = False
            supports_longlong = False
            ts = llhelper
            translate_support_code = False
            stats = "stats"
            
            def get_fail_descr_number(self, d):
                return -1

            def __init__(self, *args, **kwds):
                pass

            def nodescr(self, *args, **kwds):
                return FakeDescr()
            fielddescrof = nodescr
            calldescrof  = nodescr
            sizeof       = nodescr

            def get_fail_descr_from_number(self, no):
                return FakeFailDescr(FakeLoopToken(no))

            def execute_token(self, token):
                assert token.no == 2
                return FakeFailDescr(FakeLoopToken(1))

        driver = JitDriver(reds = ['red'], greens = ['green'])
        
        def f(green):
            red = 0
            while red < 10:
                driver.can_enter_jit(red=red, green=green)
                driver.jit_merge_point(red=red, green=green)
                red += 1
            return red

        rtyper = annotate(f, [0])
        FakeCPU.rtyper = rtyper
        translator = rtyper.annotator.translator
        translator.config.translation.gc = 'hybrid'
        cls.desc = WarmRunnerDesc(translator, CPUClass=FakeCPU)

    def test_call_helper(self):
        from pypy.rpython.llinterp import LLException

        [jd] = self.desc.jitdrivers_sd
        assert jd._assembler_call_helper(0, 0) == 3
        assert jd._assembler_call_helper(1, 0) == 10
        assert jd._assembler_call_helper(2, 0) == 10
        try:
            jd._assembler_call_helper(3, 0)
        except LLException, lle:
            assert lle[0] == self.exc_vtable
        else:
            py.test.fail("DID NOT RAISE")
