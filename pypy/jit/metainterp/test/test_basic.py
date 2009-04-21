import py
from pypy.rlib.jit import JitDriver, we_are_jitted
from pypy.jit.metainterp.warmspot import ll_meta_interp, get_stats
from pypy.jit.backend.llgraph import runner
from pypy.jit.metainterp import support, codewriter, pyjitpl, history
from pypy.jit.metainterp.policy import JitPolicy, StopAtXPolicy
from pypy import conftest
from pypy.rlib.rarithmetic import ovfcheck
from pypy.jit.metainterp.simple_optimize import Optimizer as SimpleOptimizer
from pypy.jit.metainterp.typesystem import LLTypeHelper, OOTypeHelper

def get_metainterp(func, values, CPUClass, type_system, policy,
                   listops=False):
    from pypy.annotation.policy import AnnotatorPolicy
    from pypy.annotation.model import lltype_to_annotation
    from pypy.rpython.test.test_llinterp import gengraph
    from pypy.rpython.lltypesystem import lltype

    rtyper = support.annotate(func, values, type_system=type_system)

    stats = history.Stats()
    cpu = CPUClass(rtyper, stats, False)
    graph = rtyper.annotator.translator.graphs[0]
    opt = history.Options(specialize=False, listops=listops)
    metainterp_sd = pyjitpl.MetaInterpStaticData(graph, [], cpu, stats, opt)
    metainterp = pyjitpl.MetaInterp(metainterp_sd)
    metainterp.num_green_args = 0
    return metainterp, rtyper

class JitMixin:
    basic = True
    def check_loops(self, expected=None, **check):
        get_stats().check_loops(expected=expected, **check)
    def check_loop_count(self, count):
        """NB. This is a hack; use check_tree_loop_count() or
        check_enter_count() for the real thing.
        This counts as 1 every bridge in addition to every loop; and it does
        not count at all the entry bridges from interpreter, although they
        are TreeLoops as well."""
        assert get_stats().compiled_count == count
    def check_tree_loop_count(self, count):
        assert len(get_stats().loops) == count
    def check_loop_count_at_most(self, count):
        assert get_stats().compiled_count <= count
    def check_enter_count(self, count):
        assert get_stats().enter_count == count
    def check_enter_count_at_most(self, count):
        assert get_stats().enter_count <= count
    def check_jumps(self, maxcount):
        assert get_stats().exec_jumps <= maxcount

    def meta_interp(self, *args, **kwds):
        kwds['CPUClass'] = self.CPUClass
        kwds['type_system'] = self.type_system
        return ll_meta_interp(*args, **kwds)

    def interp_operations(self, f, args, policy=None, **kwds):
        class DoneWithThisFrame(Exception):
            pass
        
        class FakeWarmRunnerDesc:
            def attach_unoptimized_bridge_from_interp(self, greenkey, newloop):
                pass
        
        if policy is None:
            policy = JitPolicy()
        metainterp, rtyper = get_metainterp(f, args, self.CPUClass,
                                            self.type_system, policy=policy,
                                            **kwds)
        cw = codewriter.CodeWriter(metainterp.staticdata, policy, self.ts)
        graph = rtyper.annotator.translator.graphs[0]
        maingraph = cw.make_one_bytecode(graph, False)
        while cw.unfinished_graphs:
            graph, called_from = cw.unfinished_graphs.pop()
            cw.make_one_bytecode(graph, False, called_from)
        metainterp.staticdata.portal_code = maingraph
        metainterp.staticdata.state = FakeWarmRunnerDesc()
        metainterp.staticdata.DoneWithThisFrame = DoneWithThisFrame
        self.metainterp = metainterp
        try:
            metainterp.compile_and_run_once(*args)
        except DoneWithThisFrame, e:
            #if conftest.option.view:
            #    metainterp.stats.view()
            return e.args[0].value
        else:
            raise Exception("FAILED")

    def check_history_(self, expected=None, **isns):
        self.metainterp.staticdata.stats.check_history(expected, **isns)


class LLJitMixin(JitMixin):
    type_system = 'lltype'
    CPUClass = runner.LLtypeCPU
    ts = LLTypeHelper()

class OOJitMixin(JitMixin):
    type_system = 'ootype'
    CPUClass = runner.OOtypeCPU
    ts = OOTypeHelper()


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
        self.check_loop_count(1)
        self.check_loops({'guard_true': 1,
                          'int_add': 1, 'int_sub': 1, 'int_gt': 1,
                          'jump': 1})
        if self.basic:
            found = 0
            for op in get_stats().loops[0]._all_operations():
                if op.getopname() == 'fail':
                    liveboxes = op.args
                    assert len(liveboxes) == 3
                    for box in liveboxes:
                        assert isinstance(box, history.BoxInt)
                    found += 1
            assert found == 1

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

    def test_chr2str(self):
        def f(n):
            s = chr(n)
            return s[0]
        res = self.interp_operations(f, [3])
        assert res == 3

    def test_unicode(self):
        def f(n):
            bytecode = u'adlfkj' + unichr(n)
            if n < len(bytecode):
                return bytecode[n]
            else:
                return u"?"
        res = self.interp_operations(f, [1])
        assert res == ord(u"d") # XXX should be "d"
        res = self.interp_operations(f, [6])
        assert res == 6
        res = self.interp_operations(f, [42])
        assert res == ord(u"?")

    def test_residual_call(self):
        def externfn(x, y):
            return x * y
        def f(n):
            return externfn(n, n+1)
        res = self.interp_operations(f, [6], policy=StopAtXPolicy(externfn))
        assert res == 42
        self.check_history_(int_add=1, int_mul=0, call=1)

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

    def test_stopatxpolicy(self):
        myjitdriver = JitDriver(greens = [], reds = ['y'])
        def internfn(y):
            return y * 3
        def externfn(y):
            return y % 4
        def f(y):
            while y >= 0:
                myjitdriver.can_enter_jit(y=y)
                myjitdriver.jit_merge_point(y=y)
                if y & 7:
                    f = internfn
                else:
                    f = externfn
                f(y)
                y -= 1
            return 42
        policy = StopAtXPolicy(externfn)
        res = self.meta_interp(f, [31], policy=policy)
        assert res == 42
        self.check_loops(int_mul=1, int_mod=0)

    def test_we_are_jitted(self):
        myjitdriver = JitDriver(greens = [], reds = ['y'])
        def f(y):
            while y >= 0:
                myjitdriver.can_enter_jit(y=y)
                myjitdriver.jit_merge_point(y=y)
                if we_are_jitted():
                    x = 1
                else:
                    x = 10
                y -= x
            return y
        assert f(55) == -5
        res = self.meta_interp(f, [55])
        assert res == -1

    def test_format(self):
        def f(n):
            return len("<%d>" % n)
        res = self.interp_operations(f, [421])
        assert res == 5

    def test_switch(self):
        def f(n):
            if n == -5:  return 12
            elif n == 2: return 51
            elif n == 7: return 1212
            else:        return 42
        res = self.interp_operations(f, [7])
        assert res == 1212

    def test_r_uint(self):
        from pypy.rlib.rarithmetic import r_uint
        myjitdriver = JitDriver(greens = [], reds = ['y'])
        def f(y):
            y = r_uint(y)
            while y > 0:
                myjitdriver.can_enter_jit(y=y)
                myjitdriver.jit_merge_point(y=y)
                y -= 1
            return y
        res = self.meta_interp(f, [10])
        assert res == 0

    def test_getfield(self):
        class A:
            pass
        a1 = A()
        a1.foo = 5
        a2 = A()
        a2.foo = 8
        def f(x):
            if x > 5:
                a = a1
            else:
                a = a2
            return a.foo * x
        res = self.interp_operations(f, [42])
        assert res == 210
        self.check_history_(getfield_gc=1)

    def test_getfield_immutable(self):
        class A:
            _immutable_ = True
        a1 = A()
        a1.foo = 5
        a2 = A()
        a2.foo = 8
        def f(x):
            if x > 5:
                a = a1
            else:
                a = a2
            return a.foo * x
        res = self.interp_operations(f, [42])
        assert res == 210
        self.check_history_(getfield_gc=0)

    def test_switch_dict(self):
        def f(x):
            if   x == 1: return 61
            elif x == 2: return 511
            elif x == 3: return -22
            elif x == 4: return 81
            elif x == 5: return 17
            elif x == 6: return 54
            elif x == 7: return 987
            elif x == 8: return -12
            elif x == 9: return 321
            return -1
        res = self.interp_operations(f, [5])
        assert res == 17

    def test_mod_ovf(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'x', 'y'])
        def f(n, x, y):
            while n > 0:
                myjitdriver.can_enter_jit(x=x, y=y, n=n)
                myjitdriver.jit_merge_point(x=x, y=y, n=n)
                n -= ovfcheck(x % y)
            return n
        res = self.meta_interp(f, [20, 1, 2])
        assert res == 0

    def test_print(self):
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        def f(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                print n
                n -= 1
            return n
        res = self.meta_interp(f, [7])
        assert res == 0

    def test_bridge_from_interpreter(self):
        mydriver = JitDriver(reds = ['n'], greens = [])

        def f(n):
            while n > 0:
                mydriver.can_enter_jit(n=n)
                mydriver.jit_merge_point(n=n)
                n -= 1

        self.meta_interp(f, [20], repeat=7)
        self.check_tree_loop_count(2)      # the loop and the entry path
        # we get:
        #    ENTER             - compile the new loop
        #    ENTER (BlackHole) - leave
        #    ENTER             - compile the entry bridge
        #    ENTER             - compile the leaving path
        self.check_enter_count(4)

    def test_bridge_from_interpreter_2(self):
        # one case for backend - computing of framesize on guard failure
        mydriver = JitDriver(reds = ['n'], greens = [])
        glob = [1]

        def f(n):
            while n > 0:
                mydriver.can_enter_jit(n=n)
                mydriver.jit_merge_point(n=n)
                if n == 17 and glob[0]:
                    glob[0] = 0
                    x = n + 1
                    y = n + 2
                    z = n + 3
                    k = n + 4
                    n -= 1
                    n += x + y + z + k
                    n -= x + y + z + k
                n -= 1

        self.meta_interp(f, [20], repeat=7)

    def test_bridge_from_interpreter_3(self):
        # one case for backend - computing of framesize on guard failure
        mydriver = JitDriver(reds = ['n', 'x', 'y', 'z', 'k'], greens = [])
        glob = [1]

        def f(n):
            x = 0
            y = 0
            z = 0
            k = 0
            while n > 0:
                mydriver.can_enter_jit(n=n, x=x, y=y, z=z, k=k)
                mydriver.jit_merge_point(n=n, x=x, y=y, z=z, k=k)
                x += 10
                y += 3
                z -= 15
                k += 4
                if n == 17 and glob[0]:
                    glob[0] = 0
                    x += n + 1
                    y += n + 2
                    z += n + 3
                    k += n + 4
                    n -= 1
                n -= 1
            return x + 2*y + 3*z + 5*k + 13*n

        # XXX explodes on normal optimize.py
        res = self.meta_interp(f, [20], repeat=7, optimizer=SimpleOptimizer)
        assert res == f(20)

    def test_bridge_from_interpreter_4(self):
        jitdriver = JitDriver(reds = ['n', 'k'], greens = [])
        
        def f(n, k):
            while n > 0:
                jitdriver.can_enter_jit(n=n, k=k)
                jitdriver.jit_merge_point(n=n, k=k)
                if k:
                    n -= 2
                else:
                    n -= 1
            return n + k

        from pypy.rpython.test.test_llinterp import get_interpreter, clear_tcache
        from pypy.jit.metainterp.warmspot import WarmRunnerDesc
        from pypy.jit.metainterp.simple_optimize import Optimizer as SimpleOptimizer

        interp, graph = get_interpreter(f, [0, 0], backendopt=False,
                                        inline_threshold=0)
        clear_tcache()
        translator = interp.typer.annotator.translator
        warmrunnerdesc = WarmRunnerDesc(translator,
                                        CPUClass=self.CPUClass,
                                        optimizer=SimpleOptimizer)
        warmrunnerdesc.state.set_param_threshold(3)          # for tests
        warmrunnerdesc.state.set_param_trace_eagerness(0)    # for tests
        warmrunnerdesc.finish()
        for n, k in [(20, 0), (20, 1)]:
            interp.eval_graph(graph, [n, k])

    def test_casts(self):
        from pypy.rpython.lltypesystem import lltype, llmemory
        
        TP = lltype.GcStruct('x')
        def f(p):
            n = lltype.cast_ptr_to_int(p)
            return lltype.cast_int_to_ptr(lltype.Ptr(TP), n)

        x = lltype.malloc(TP)
        expected = lltype.cast_opaque_ptr(llmemory.GCREF, x)
        assert self.interp_operations(f, [x]) == expected

    def test_oops_on_nongc(self):
        from pypy.rpython.lltypesystem import lltype
        
        TP = lltype.Struct('x')
        def f(p1, p2):
            a = p1 is p2
            b = p1 is not p2
            c = bool(p1)
            d = not bool(p2)
            return a + b + c + d
        x = lltype.malloc(TP, flavor='raw')
        expected = f(x, x)
        assert self.interp_operations(f, [x, x]) == expected
        lltype.free(x, flavor='raw')

    def test_instantiate_classes(self):
        class Base: pass
        class A(Base): foo = 72
        class B(Base): foo = 8
        def f(n):
            if n > 5:
                cls = A
            else:
                cls = B
            return cls().foo
        res = self.interp_operations(f, [3])
        assert res == 8
        res = self.interp_operations(f, [13])
        assert res == 72


class TestOOtype(BasicTests, OOJitMixin):
    def skip(self):
        py.test.skip('in-progress')

    test_format = skip
    test_oops_on_nongc = skip
    test_instantiate_classes = skip

    test_print = skip
    test_bridge_from_interpreter_2 = skip
    test_bridge_from_interpreter_3 = skip
    test_bridge_from_interpreter_4 = skip
    test_casts = skip


class TestLLtype(BasicTests, LLJitMixin):
    pass
