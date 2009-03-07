import py
from pypy.rlib.jit import JitDriver
from pypy.jit.metainterp.warmspot import ll_meta_interp, get_stats
from pypy.jit.backend.llgraph import runner
from pypy.jit.metainterp import support, codewriter, pyjitpl, history
from pypy.jit.metainterp.policy import JitPolicy, StopAtXPolicy

def get_metainterp(func, values, CPUClass, type_system, policy):
    from pypy.annotation.policy import AnnotatorPolicy
    from pypy.annotation.model import lltype_to_annotation
    from pypy.rpython.test.test_llinterp import gengraph
    from pypy.rpython.lltypesystem import lltype

    rtyper = support.annotate(func, values, type_system=type_system)

    stats = history.Stats()
    cpu = CPUClass(rtyper, stats, False)
    graph = rtyper.annotator.translator.graphs[0]
    metainterp = pyjitpl.OOMetaInterp(graph, [], cpu, stats, False)
    metainterp.num_green_args = 0
    return metainterp, rtyper

class JitMixin:
    basic = True
    def check_loops(self, expected=None, **check):
        get_stats().check_loops(expected=expected, **check)
    def check_loop_count(self, count):
        assert len(get_stats().loops) == count
    def check_loop_count_at_most(self, count):
        assert len(get_stats().loops) <= count
    def check_jumps(self, maxcount):
        assert get_stats().exec_jumps <= maxcount

class LLJitMixin(JitMixin):
    type_system = 'lltype'
    CPUClass = runner.CPU

    def meta_interp(self, *args, **kwds):
        kwds['CPUClass'] = self.CPUClass
        return ll_meta_interp(*args, **kwds)

    def interp_operations(self, f, args, policy=None):
        class DoneWithThisFrame(Exception):
            pass
        
        class FakeWarmRunnderDesc:
            num_green_args = 0
        
        if policy is None:
            policy = JitPolicy()
        metainterp, rtyper = get_metainterp(f, args, self.CPUClass,
                                            self.type_system, policy=policy)
        cw = codewriter.CodeWriter(metainterp, policy)
        graph = rtyper.annotator.translator.graphs[0]
        maingraph = cw.make_one_bytecode(graph, False)
        while cw.unfinished_graphs:
            graph = cw.unfinished_graphs.pop()
            cw.make_one_bytecode(graph, False)
        metainterp.portal_code = maingraph
        metainterp.cpu.set_meta_interp(metainterp)
        metainterp.delete_history()
        metainterp.warmrunnerdesc = FakeWarmRunnderDesc
        metainterp.DoneWithThisFrame = DoneWithThisFrame
        self.metainterp = metainterp
        try:
            metainterp.compile_and_run(args)
        except DoneWithThisFrame, e:
            return e.args[0].value
        else:
            raise Exception("FAILED")

    def check_history_(self, expected=None, **isns):
        self.metainterp.stats.check_history(expected, **isns)

class OOJitMixin(JitMixin):
    type_system = 'ootype'
    CPUClass = runner.CPU
    def meta_interp(self, *args, **kwds):
        py.test.skip("not for ootype right now")

    def interp_operations(self, f, args, policy=None):
        py.test.skip("not for ootype right now")

class BasicTests:    

    def test_basic(self):
        def f(x, y):
            return x + y
        res = self.interp_operations(f, [40, 2])
        assert res == 42

    def test_basic_mp(self):
        def f(x, y):
            return x + y
        res = self.interp_operations(f, [40, 2])
        assert res == 42

    def test_basic_inst(self):
        class A:
            pass
        def f(n):
            a = A()
            a.x = n
            return a.x
        res = self.interp_operations(f, [42])
        assert res == 42

    def test_direct_call(self):
        def g(n):
            return n + 2
        def f(a, b):
            return g(a) + g(b)
        res = self.interp_operations(f, [8, 98])
        assert res == 110

    def test_direct_call_with_guard(self):
        def g(n):
            if n < 0:
                return 0
            return n + 2
        def f(a, b):
            return g(a) + g(b)
        res = self.interp_operations(f, [8, 98])
        assert res == 110

    def test_loop(self):
        myjitdriver = JitDriver(greens = [], reds = ['x', 'y', 'res'])
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
        self.check_loops({'merge_point': 1, 'guard_true': 1,
                          'int_add': 1, 'int_sub': 1, 'int_gt': 1,
                          'jump': 1})

    def test_string(self):
        def f(n):
            bytecode = 'adlfkj' + chr(n)
            if n < len(bytecode):
                return bytecode[n]
            else:
                return "?"
        res = self.interp_operations(f, [1])
        assert res == ord("d") # XXX should be "d"
        res = self.interp_operations(f, [6])
        assert res == 6
        res = self.interp_operations(f, [42])
        assert res == ord("?")

    def test_residual_call(self):
        def externfn(x, y):
            return x * y
        def f(n):
            return externfn(n, n+1)
        res = self.interp_operations(f, [6], policy=StopAtXPolicy(externfn))
        assert res == 42
        self.check_history_(int_add=1, int_mul=0, call__4=1)

    def test_constant_across_mp(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        class X(object):
            pass
        def f(n):
            while n > -100:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                x = X()
                x.arg = 5
                if n <= 0: break
                n -= x.arg
                x.arg = 6   # prevents 'x.arg' from being annotated as constant
            return n
        res = self.meta_interp(f, [31])
        assert res == -4


class TestOOtype(BasicTests, OOJitMixin):
    pass

class TestLLtype(BasicTests, LLJitMixin):
    pass
