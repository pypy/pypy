import py
from pypy.jit.metainterp.warmspot import rpython_ll_meta_interp, ll_meta_interp
from pypy.jit.metainterp.test import test_basic
from pypy.jit.backend.llgraph import runner
from pypy.rlib.jit import JitDriver
from pypy.jit.conftest import option


class BasicTest:

    CPUClass = None
    type_system = None

    def test_loop_1(self):
        if not option.run_slow_tests:
            py.test.skip("use --slow to execute this long-running test")
        jitdriver = JitDriver(greens = [], reds = ['i', 'total'])
        def f(i):
            total = 0
            while i > 3:
                jitdriver.can_enter_jit(i=i, total=total)
                jitdriver.jit_merge_point(i=i, total=total)
                total += i
                i -= 1
            return total * 10
        res = ll_meta_interp(f, [10], CPUClass=self.CPUClass,
                             type_system=self.type_system)
        assert res == 490
        res = rpython_ll_meta_interp(f, [10], loops=1, CPUClass=self.CPUClass,
                                     type_system=self.type_system)
        assert res == 490

    def test_loop_2(self):
        # this test runs even without the --slow option, to see at least one
        jitdriver = JitDriver(greens = [], reds = ['i', 'total'])
        def f(i):
            total = 0
            while i > 3:
                jitdriver.can_enter_jit(i=i, total=total)
                jitdriver.jit_merge_point(i=i, total=total)
                total += i
                if i >= 10:
                    i -= 2
                i -= 1
            return total * 10
        res = ll_meta_interp(f, [17], CPUClass=self.CPUClass,
                             type_system=self.type_system)
        assert res == (17+14+11+8+7+6+5+4) * 10
        res = rpython_ll_meta_interp(f, [17], loops=2, CPUClass=self.CPUClass,
                                     type_system=self.type_system)
        assert res == (17+14+11+8+7+6+5+4) * 10


class TestBasicLLtype(BasicTest):

    CPUClass = runner.LLtypeCPU
    type_system = 'lltype'

# we need to decide if we want the llgraph backend to be translatable or not
## class TestBasicOOtype(BasicTest):

##     CPUClass = runner.OOtypeCPU
##     type_system = 'ootype'
    

class LLInterpJitMixin:
    CPUClass = runner.LLtypeCPU
    type_system = 'lltype'
    basic = False

    def meta_interp(self, *args, **kwds):
        if not option.run_slow_tests:
            py.test.skip("use --slow to execute this long-running test")
        kwds.setdefault('CPUClass', self.CPUClass)
        return rpython_ll_meta_interp(*args, **kwds)

    def check_history(self, expected=None, **check):
        pass
    def check_loops(self, expected=None, **check):
        pass
    def check_loop_count(self, count):
        pass
    def check_tree_loop_count(self, count):
        pass
    def check_loop_count_at_most(self, count):
        pass
    def check_enter_count(self, count):
        pass
    def check_enter_count_at_most(self, count):
        pass
    def check_jumps(self, maxcount):
        pass

    def interp_operations(self, *args, **kwds):
        py.test.skip("interp operations makes no sense when translated")
