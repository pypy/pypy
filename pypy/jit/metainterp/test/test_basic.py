import py
import sys
from pypy.rlib.jit import JitDriver, we_are_jitted, hint, dont_look_inside
from pypy.rlib.jit import OPTIMIZER_FULL, OPTIMIZER_SIMPLE
from pypy.jit.metainterp.warmspot import ll_meta_interp, get_stats
from pypy.jit.backend.llgraph import runner
from pypy.jit.metainterp import support, codewriter, pyjitpl, history
from pypy.jit.metainterp.policy import JitPolicy, StopAtXPolicy
from pypy import conftest
from pypy.rlib.rarithmetic import ovfcheck
from pypy.jit.metainterp.typesystem import LLTypeHelper, OOTypeHelper
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype

def _get_bare_metainterp(func, values, CPUClass, type_system,
                         listops=False):
    from pypy.annotation.policy import AnnotatorPolicy
    from pypy.annotation.model import lltype_to_annotation
    from pypy.rpython.test.test_llinterp import gengraph

    rtyper = support.annotate(func, values, type_system=type_system)

    stats = history.Stats()
    cpu = CPUClass(rtyper, stats, False)
    graphs = rtyper.annotator.translator.graphs
    opt = history.Options(listops=listops)
    metainterp_sd = pyjitpl.MetaInterpStaticData(graphs[0], cpu, stats, opt)
    metainterp_sd.finish_setup(optimizer="bogus")
    metainterp = pyjitpl.MetaInterp(metainterp_sd)
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
    def check_aborted_count(self, maxcount):
        assert get_stats().aborted_count == maxcount

    def meta_interp(self, *args, **kwds):
        kwds['CPUClass'] = self.CPUClass
        kwds['type_system'] = self.type_system
        if "backendopt" not in kwds:
            kwds["backendopt"] = False
        return ll_meta_interp(*args, **kwds)

    def interp_operations(self, f, args, **kwds):
        from pypy.jit.metainterp import simple_optimize

        class DoneWithThisFrame(Exception):
            pass

        class DoneWithThisFrameRef(DoneWithThisFrame):
            def __init__(self, cpu, *args):
                DoneWithThisFrame.__init__(self, *args)
        
        class FakeWarmRunnerState:
            def attach_unoptimized_bridge_from_interp(self, greenkey, newloop):
                pass

            # pick the optimizer this way
            optimize_loop = staticmethod(simple_optimize.optimize_loop)
            optimize_bridge = staticmethod(simple_optimize.optimize_bridge)

            trace_limit = sys.maxint
            debug_level = 2
        
        metainterp, rtyper = _get_bare_metainterp(f, args, self.CPUClass,
                                                  self.type_system,
                                                  **kwds)
        portal_graph = rtyper.annotator.translator.graphs[0]
        cw = codewriter.CodeWriter(rtyper)
        
        graphs = cw.find_all_graphs(portal_graph, None, JitPolicy(),
                                    self.CPUClass.supports_floats)
        cw._start(metainterp.staticdata, None)
        portal_graph.func._jit_unroll_safe_ = True
        maingraph = cw.make_one_bytecode((portal_graph, None), False)
        cw.finish_making_bytecodes()
        metainterp.staticdata.portal_code = maingraph
        metainterp.staticdata._class_sizes = cw.class_sizes
        metainterp.staticdata.state = FakeWarmRunnerState()
        metainterp.staticdata.DoneWithThisFrameInt = DoneWithThisFrame
        metainterp.staticdata.DoneWithThisFrameRef = DoneWithThisFrameRef
        metainterp.staticdata.DoneWithThisFrameFloat = DoneWithThisFrame
        self.metainterp = metainterp
        try:
            metainterp.compile_and_run_once(*args)
        except DoneWithThisFrame, e:
            #if conftest.option.view:
            #    metainterp.stats.view()
            return e.args[0]
        else:
            raise Exception("FAILED")

    def check_history_(self, expected=None, **isns):
        self.metainterp.staticdata.stats.check_history(expected, **isns)


class LLJitMixin(JitMixin):
    type_system = 'lltype'
    CPUClass = runner.LLtypeCPU

    @staticmethod
    def Ptr(T):
        return lltype.Ptr(T)

    @staticmethod
    def GcStruct(name, *fields, **kwds):
        S = lltype.GcStruct(name, *fields, **kwds)
        return S

    malloc = staticmethod(lltype.malloc)
    nullptr = staticmethod(lltype.nullptr)

    @staticmethod
    def malloc_immortal(T):
        return lltype.malloc(T, immortal=True)

    def _get_NODE(self):
        NODE = lltype.GcForwardReference()
        NODE.become(lltype.GcStruct('NODE', ('value', lltype.Signed),
                                            ('next', lltype.Ptr(NODE))))
        return NODE
    
class OOJitMixin(JitMixin):
    type_system = 'ootype'
    CPUClass = runner.OOtypeCPU

    @staticmethod
    def Ptr(T):
        return T

    @staticmethod
    def GcStruct(name, *fields, **kwds):
        if 'hints' in kwds:
            kwds['_hints'] = kwds['hints']
            del kwds['hints']
        I = ootype.Instance(name, ootype.ROOT, dict(fields), **kwds)
        return I

    malloc = staticmethod(ootype.new)
    nullptr = staticmethod(ootype.null)

    @staticmethod
    def malloc_immortal(T):
        return ootype.new(T)

    def _get_NODE(self):
        NODE = ootype.Instance('NODE', ootype.ROOT, {})
        NODE._add_fields({'value': ootype.Signed,
                          'next': NODE})
        return NODE


class BasicTests:    

    def test_basic(self):
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
                if op.getopname() == 'guard_true':
                    liveboxes = op.fail_args
                    assert len(liveboxes) == 3
                    for box in liveboxes:
                        assert isinstance(box, history.BoxInt)
                    found += 1
            assert found == 1

    def test_loops_are_transient(self):
        import gc, weakref
        myjitdriver = JitDriver(greens = [], reds = ['x', 'y', 'res'])
        def f(x, y):
            res = 0
            while y > 0:
                myjitdriver.can_enter_jit(x=x, y=y, res=res)
                myjitdriver.jit_merge_point(x=x, y=y, res=res)
                res += x
                if y%2:
                    res *= 2
                y -= 1
            return res
        wr_loops = []
        old_init = history.TreeLoop.__init__.im_func
        try:
            def track_init(self, name):
                old_init(self, name)
                wr_loops.append(weakref.ref(self))
            history.TreeLoop.__init__ = track_init
            res = self.meta_interp(f, [6, 15], no_stats=True)
        finally:
            history.TreeLoop.__init__ = old_init
            
        assert res == f(6, 15)
        gc.collect()

        assert not [wr for wr in wr_loops if wr()]

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
        @dont_look_inside
        def externfn(x, y):
            return x * y
        def f(n):
            return externfn(n, n+1)
        res = self.interp_operations(f, [6])
        assert res == 42
        self.check_history_(int_add=1, int_mul=0, call=1, guard_no_exception=0)

    def test_residual_call_pure(self):
        def externfn(x, y):
            return x * y
        externfn._pure_function_ = True
        def f(n):
            n = hint(n, promote=True)
            return externfn(n, n+1)
        res = self.interp_operations(f, [6])
        assert res == 42
        self.check_history_(int_add=0, int_mul=0, call=0)

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
        res = self.interp_operations(f, [12311])
        assert res == 42

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

    def test_setfield_bool(self):
        class A:
            def __init__(self):
                self.flag = True
        myjitdriver = JitDriver(greens = [], reds = ['n', 'obj'])
        def f(n):
            obj = A()
            res = False
            while n > 0:
                myjitdriver.can_enter_jit(n=n, obj=obj)
                myjitdriver.jit_merge_point(n=n, obj=obj)
                obj.flag = False
                n -= 1
            return res
        res = self.meta_interp(f, [7])
        assert type(res) == bool
        assert not res

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
        res = self.interp_operations(f, [15])
        assert res == -1

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

    def test_abs(self):
        myjitdriver = JitDriver(greens = [], reds = ['i', 't'])
        def f(i):
            t = 0
            while i < 10:
                myjitdriver.can_enter_jit(i=i, t=t)
                myjitdriver.jit_merge_point(i=i, t=t)
                t += abs(i)
                i += 1
            return t
        res = self.meta_interp(f, [-5])
        assert res == 5+4+3+2+1+0+1+2+3+4+5+6+7+8+9

    def test_float(self):
        myjitdriver = JitDriver(greens = [], reds = ['x', 'y', 'res'])
        def f(x, y):
            x = float(x)
            y = float(y)
            res = 0.0
            while y > 0.0:
                myjitdriver.can_enter_jit(x=x, y=y, res=res)
                myjitdriver.jit_merge_point(x=x, y=y, res=res)
                res += x
                y -= 1.0
            return res
        res = self.meta_interp(f, [6, 7])
        assert res == 42.0
        self.check_loop_count(1)
        self.check_loops({'guard_true': 1,
                          'float_add': 1, 'float_sub': 1, 'float_gt': 1,
                          'jump': 1})

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
        class Global:
            pass
        glob = Global()

        def f(n):
            glob.x = 1
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
                if n == 17 and glob.x:
                    glob.x = 0
                    x += n + 1
                    y += n + 2
                    z += n + 3
                    k += n + 4
                    n -= 1
                n -= 1
            return x + 2*y + 3*z + 5*k + 13*n

        res = self.meta_interp(f, [20], repeat=7)
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
        
        interp, graph = get_interpreter(f, [0, 0], backendopt=False,
                                        inline_threshold=0, type_system=self.type_system)
        clear_tcache()
        translator = interp.typer.annotator.translator
        translator.config.translation.gc = "boehm"
        warmrunnerdesc = WarmRunnerDesc(translator,
                                        CPUClass=self.CPUClass)
        warmrunnerdesc.state.set_param_threshold(3)          # for tests
        warmrunnerdesc.state.set_param_trace_eagerness(0)    # for tests
        warmrunnerdesc.finish()
        for n, k in [(20, 0), (20, 1)]:
            interp.eval_graph(graph, [n, k])

    def test_bridge_leaving_interpreter_5(self):
        mydriver = JitDriver(reds = ['n', 'x'], greens = [])
        class Global:
            pass
        glob = Global()

        def f(n):
            x = 0
            glob.x = 1
            while n > 0:
                mydriver.can_enter_jit(n=n, x=x)
                mydriver.jit_merge_point(n=n, x=x)
                glob.x += 1
                x += 3
                n -= 1
            glob.x += 100
            return glob.x + x
        res = self.meta_interp(f, [20], repeat=7)
        assert res == f(20)

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

    def test_instantiate_does_not_call(self):
        mydriver = JitDriver(reds = ['n', 'x'], greens = [])
        class Base: pass
        class A(Base): foo = 72
        class B(Base): foo = 8

        def f(n):
            x = 0
            while n > 0:
                mydriver.can_enter_jit(n=n, x=x)
                mydriver.jit_merge_point(n=n, x=x)
                if n % 2 == 0:
                    cls = A
                else:
                    cls = B
                inst = cls()
                x += inst.foo
                n -= 1
            return x
        res = self.meta_interp(f, [20], optimizer=OPTIMIZER_SIMPLE)
        assert res == f(20)
        self.check_loops(call=0)

    def test_zerodivisionerror(self):
        # test the case of exception-raising operation that is not delegated
        # to the backend at all: ZeroDivisionError
        from pypy.rpython.lltypesystem.lloperation import llop
        #
        def f(n):
            try:
                return llop.int_mod_ovf_zer(lltype.Signed, 5, n)
            except ZeroDivisionError:
                return -666
        res = self.interp_operations(f, [0])
        assert res == -666
        #
        def f(n):
            try:
                return llop.int_floordiv_ovf_zer(lltype.Signed, 6, n)
            except ZeroDivisionError:
                return -667
        res = self.interp_operations(f, [0])
        assert res == -667

    def test_div_overflow(self):
        import sys
        from pypy.rpython.lltypesystem.lloperation import llop
        myjitdriver = JitDriver(greens = [], reds = ['x', 'y', 'res'])
        def f(x, y):
            res = 0
            while y > 0:
                myjitdriver.can_enter_jit(x=x, y=y, res=res)
                myjitdriver.jit_merge_point(x=x, y=y, res=res)
                try:
                    res += llop.int_floordiv_ovf(lltype.Signed,
                                                 -sys.maxint-1, x)
                    x += 5
                except OverflowError:
                    res += 100
                y -= 1
            return res
        res = self.meta_interp(f, [-41, 16])
        assert res == ((-sys.maxint-1) // (-41) +
                       (-sys.maxint-1) // (-36) +
                       (-sys.maxint-1) // (-31) +
                       (-sys.maxint-1) // (-26) +
                       (-sys.maxint-1) // (-21) +
                       (-sys.maxint-1) // (-16) +
                       (-sys.maxint-1) // (-11) +
                       (-sys.maxint-1) // (-6) +
                       100 * 8)

    def test_isinstance(self):
        class A:
            pass
        class B(A):
            pass
        def fn(n):
            if n:
                obj = A()
            else:
                obj = B()
            return isinstance(obj, B)
        res = self.interp_operations(fn, [0])
        assert res
        self.check_history_(guard_class=1)
        res = self.interp_operations(fn, [1])
        assert not res

    def test_assert_isinstance(self):
        class A:
            pass
        class B(A):
            pass
        def fn(n):
            # this should only be called with n != 0
            if n:
                obj = B()
                obj.a = n
            else:
                obj = A()
                obj.a = 17
            assert isinstance(obj, B)
            return obj.a
        res = self.interp_operations(fn, [1])
        assert res == 1
        self.check_history_(guard_class=0, instanceof=0)

    def test_r_dict(self):
        from pypy.rlib.objectmodel import r_dict
        class FooError(Exception):
            pass
        def myeq(n, m):
            return n == m
        def myhash(n):
            if n < 0:
                raise FooError
            return -n
        def f(n):
            d = r_dict(myeq, myhash)
            for i in range(10):
                d[i] = i*i
            try:
                return d[n]
            except FooError:
                return 99
        res = self.interp_operations(f, [5])
        assert res == f(5)

    def test_long_long(self):
        from pypy.rlib.rarithmetic import r_longlong, intmask
        def g(n, m, o):
            # This function should be completely marked as residual by
            # codewriter.py on 32-bit platforms.  On 64-bit platforms,
            # this function should be JITted and the test should pass too.
            n = r_longlong(n)
            m = r_longlong(m)
            return intmask((n*m) // o)
        def f(n, m, o):
            return g(n, m, o) // 3
        res = self.interp_operations(f, [1000000000, 90, 91])
        assert res == (1000000000 * 90 // 91) // 3

    def test_free_object(self):
        import weakref
        from pypy.rlib import rgc
        from pypy.rpython.lltypesystem.lloperation import llop
        myjitdriver = JitDriver(greens = [], reds = ['n', 'x'])
        class X(object):
            pass
        def main(n, x):
            while n > 0:
                myjitdriver.can_enter_jit(n=n, x=x)
                myjitdriver.jit_merge_point(n=n, x=x)
                n -= x.foo
        def g(n):
            x = X()
            x.foo = 2
            main(n, x)
            x.foo = 5
            return weakref.ref(x)
        def f(n):
            r = g(n)
            rgc.collect(); rgc.collect(); rgc.collect()
            return r() is None
        #
        assert f(30) == 1
        res = self.meta_interp(f, [30], no_stats=True)
        assert res == 1

    def test_pass_around(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'x'])

        def call():
            pass

        def f(n, x):
            while n > 0:
                myjitdriver.can_enter_jit(n=n, x=x)
                myjitdriver.jit_merge_point(n=n, x=x)
                if n % 2:
                    call()
                    if n == 8:
                        return x
                    x = 3
                else:
                    x = 5
                n -= 1
            return 0

        self.meta_interp(f, [40, 0])

    def test_const_inputargs(self):
        myjitdriver = JitDriver(greens = ['m'], reds = ['n', 'x'])
        def f(n, x):
            m = 0x7FFFFFFF
            while n > 0:
                myjitdriver.can_enter_jit(m=m, n=n, x=x)
                myjitdriver.jit_merge_point(m=m, n=n, x=x)
                x = 42
                n -= 1
                m = m >> 1
            return x

        res = self.meta_interp(f, [50, 1],
                               optimizer=OPTIMIZER_SIMPLE)
        assert res == 42

    def test_set_param(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'x'])
        def g(n):
            x = 0
            while n > 0:
                myjitdriver.can_enter_jit(n=n, x=x)
                myjitdriver.jit_merge_point(n=n, x=x)
                n -= 1
                x += n
            return x
        def f(n, threshold):
            myjitdriver.set_param('threshold', threshold)
            return g(n)

        res = self.meta_interp(f, [10, 3])
        assert res == 9 + 8 + 7 + 6 + 5 + 4 + 3 + 2 + 1 + 0
        self.check_tree_loop_count(1)

        res = self.meta_interp(f, [10, 13])
        assert res == 9 + 8 + 7 + 6 + 5 + 4 + 3 + 2 + 1 + 0
        self.check_tree_loop_count(0)

    def test_dont_look_inside(self):
        @dont_look_inside
        def g(a, b):
            return a + b
        def f(a, b):
            return g(a, b)
        res = self.interp_operations(f, [3, 5])
        assert res == 8
        self.check_history_(int_add=0, call=1)

    def test_listcomp(self):
        myjitdriver = JitDriver(greens = [], reds = ['x', 'y', 'lst'])
        def f(x, y):
            lst = [0, 0, 0]
            while y > 0:
                myjitdriver.can_enter_jit(x=x, y=y, lst=lst)
                myjitdriver.jit_merge_point(x=x, y=y, lst=lst)
                lst = [i+x for i in lst if i >=0]
                y -= 1
            return lst[0]
        res = self.meta_interp(f, [6, 7], listcomp=True, backendopt=True, listops=True)
        # XXX: the loop looks inefficient
        assert res == 42

    def test_tuple_immutable(self):
        def new(a, b):
            return a, b
        def f(a, b):
            tup = new(a, b)
            return tup[1]
        res = self.interp_operations(f, [3, 5])
        assert res == 5
        self.check_history_(setfield_gc=2, getfield_gc_pure=1)

    def test_oosend_look_inside_only_one(self):
        class A:
            pass
        class B(A):
            def g(self):
                return 123
        class C(A):
            @dont_look_inside
            def g(self):
                return 456
        def f(n):
            if n > 3:
                x = B()
            else:
                x = C()
            return x.g() + x.g()
        res = self.interp_operations(f, [10])
        assert res == 123 * 2
        res = self.interp_operations(f, [-10])
        assert res == 456 * 2

    def test_residual_external_call(self):
        import math
        myjitdriver = JitDriver(greens = [], reds = ['x', 'y', 'res'])
        def f(x, y):
            x = float(x)
            res = 0
            while y > 0:
                myjitdriver.can_enter_jit(x=x, y=y, res=res)
                myjitdriver.jit_merge_point(x=x, y=y, res=res)
                # this is an external call that the default policy ignores
                rpart, ipart = math.modf(x)
                res += ipart
                y -= 1
            return res
        res = self.meta_interp(f, [6, 7])
        assert res == 42
        self.check_loop_count(1)
        self.check_loops(call=1)


class TestOOtype(BasicTests, OOJitMixin):

    def test_oohash(self):
        def f(n):
            s = ootype.oostring(n, -1)
            return s.ll_hash()
        res = self.interp_operations(f, [5])
        assert res == ootype.oostring(5, -1).ll_hash()

    def test_identityhash(self):
        A = ootype.Instance("A", ootype.ROOT)
        def f():
            obj1 = ootype.new(A)
            obj2 = ootype.new(A)
            return ootype.identityhash(obj1) == ootype.identityhash(obj2)
        assert not f()
        res = self.interp_operations(f, [])
        assert not res

    def test_oois(self):
        A = ootype.Instance("A", ootype.ROOT)
        def f(n):
            obj1 = ootype.new(A)
            if n:
                obj2 = obj1
            else:
                obj2 = ootype.new(A)
            return obj1 is obj2
        res = self.interp_operations(f, [0])
        assert not res
        res = self.interp_operations(f, [1])
        assert res

    def test_oostring_instance(self):
        A = ootype.Instance("A", ootype.ROOT)
        B = ootype.Instance("B", ootype.ROOT)
        def f(n):
            obj1 = ootype.new(A)
            obj2 = ootype.new(B)
            s1 = ootype.oostring(obj1, -1)
            s2 = ootype.oostring(obj2, -1)
            ch1 = s1.ll_stritem_nonneg(1)
            ch2 = s2.ll_stritem_nonneg(1)
            return ord(ch1) + ord(ch2)
        res = self.interp_operations(f, [0])
        assert res == ord('A') + ord('B')

    def test_r_dict(self):
        py.test.skip('in-progress')


    def test_subclassof(self):
        A = ootype.Instance("A", ootype.ROOT)
        B = ootype.Instance("B", A)
        clsA = ootype.runtimeClass(A)
        clsB = ootype.runtimeClass(B)
        myjitdriver = JitDriver(greens = [], reds = ['n', 'flag', 'res'])

        def getcls(flag):
            if flag:
                return clsA
            else:
                return clsB

        def f(flag, n):
            res = True
            while n > -100:
                myjitdriver.can_enter_jit(n=n, flag=flag, res=res)
                myjitdriver.jit_merge_point(n=n, flag=flag, res=res)
                cls = getcls(flag)
                n -= 1
                res = ootype.subclassof(cls, clsB)
            return res

        res = self.meta_interp(f, [1, 100],
                               policy=StopAtXPolicy(getcls),
                               optimizer=OPTIMIZER_SIMPLE)
        assert not res
        
        res = self.meta_interp(f, [0, 100],
                               policy=StopAtXPolicy(getcls),
                               optimizer=OPTIMIZER_SIMPLE)
        assert res




class BaseLLtypeTests(BasicTests):

    def test_identityhash(self):
        A = lltype.GcStruct("A")
        def f():
            obj1 = lltype.malloc(A)
            obj2 = lltype.malloc(A)
            return lltype.identityhash(obj1) == lltype.identityhash(obj2)
        assert not f()
        res = self.interp_operations(f, [])
        assert not res

    def test_oops_on_nongc(self):
        from pypy.rpython.lltypesystem import lltype
        
        TP = lltype.Struct('x')
        def f(p1, p2):
            a = p1 is p2
            b = p1 is not p2
            c = bool(p1)
            d = not bool(p2)
            return 1000*a + 100*b + 10*c + d
        x = lltype.malloc(TP, flavor='raw')
        expected = f(x, x)
        assert self.interp_operations(f, [x, x]) == expected
        lltype.free(x, flavor='raw')

    def test_casts(self):
        if not self.basic:
            py.test.skip("test written in a style that "
                         "means it's frontend only")
        from pypy.rpython.lltypesystem import lltype, llmemory
        
        TP = lltype.GcStruct('x')
        def f(p):
            n = lltype.cast_ptr_to_int(p)
            return n

        x = lltype.malloc(TP)
        res = self.interp_operations(f, [x])
        expected = self.metainterp.cpu.do_cast_ptr_to_int(
            history.BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, x))).value
        assert res == expected

class TestLLtype(BaseLLtypeTests, LLJitMixin):
    pass
