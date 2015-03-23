
from rpython.rlib.jit import JitDriver, JitHookInterface, Counters
from rpython.rlib import jit_hooks
from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.jit.codewriter.policy import JitPolicy
from rpython.jit.metainterp.resoperation import rop
from rpython.rtyper.annlowlevel import hlstr
from rpython.jit.metainterp.jitprof import Profiler, EmptyProfiler


class JitHookInterfaceTests(object):
    # !!!note!!! - don't subclass this from the backend. Subclass the LL
    # class later instead
    def test_abort_quasi_immut(self):
        reasons = []

        class MyJitIface(JitHookInterface):
            def on_abort(self, reason, jitdriver, greenkey, greenkey_repr, logops, operations):
                assert jitdriver is myjitdriver
                assert len(greenkey) == 1
                reasons.append(reason)
                assert greenkey_repr == 'blah'
                assert len(operations) > 1

        iface = MyJitIface()

        myjitdriver = JitDriver(greens=['foo'], reds=['x', 'total'],
                                get_printable_location=lambda *args: 'blah')

        class Foo:
            _immutable_fields_ = ['a?']

            def __init__(self, a):
                self.a = a

        def f(a, x):
            foo = Foo(a)
            total = 0
            while x > 0:
                myjitdriver.jit_merge_point(foo=foo, x=x, total=total)
                # read a quasi-immutable field out of a Constant
                total += foo.a
                foo.a += 1
                x -= 1
            return total
        #
        assert f(100, 7) == 721
        res = self.meta_interp(f, [100, 7], policy=JitPolicy(iface))
        assert res == 721
        assert reasons == [Counters.ABORT_FORCE_QUASIIMMUT] * 2

    def test_on_compile(self):
        called = []

        class MyJitIface(JitHookInterface):
            def after_compile(self, di):
                called.append(("compile", di.greenkey[1].getint(),
                               di.greenkey[0].getint(), di.type))

            def before_compile(self, di):
                called.append(("optimize", di.greenkey[1].getint(),
                               di.greenkey[0].getint(), di.type))

            #def before_optimize(self, jitdriver, logger, looptoken, oeprations,
            #                   type, greenkey):
            #    called.append(("trace", greenkey[1].getint(),
            #                   greenkey[0].getint(), type))

        iface = MyJitIface()

        driver = JitDriver(greens = ['n', 'm'], reds = ['i'])

        def loop(n, m):
            i = 0
            while i < n + m:
                driver.can_enter_jit(n=n, m=m, i=i)
                driver.jit_merge_point(n=n, m=m, i=i)
                i += 1

        self.meta_interp(loop, [1, 4], policy=JitPolicy(iface))
        assert called == [#("trace", 4, 1, "loop"),
                          ("optimize", 4, 1, "loop"),
                          ("compile", 4, 1, "loop")]
        self.meta_interp(loop, [2, 4], policy=JitPolicy(iface))
        assert called == [#("trace", 4, 1, "loop"),
                          ("optimize", 4, 1, "loop"),
                          ("compile", 4, 1, "loop"),
                          #("trace", 4, 2, "loop"),
                          ("optimize", 4, 2, "loop"),
                          ("compile", 4, 2, "loop")]

    def test_on_compile_bridge(self):
        called = []
        
        class MyJitIface(JitHookInterface):
            def after_compile(self, di):
                called.append("compile")

            def after_compile_bridge(self, di):
                called.append("compile_bridge")

            def before_compile_bridge(self, di):
                called.append("before_compile_bridge")
            
        driver = JitDriver(greens = ['n', 'm'], reds = ['i'])

        def loop(n, m):
            i = 0
            while i < n + m:
                driver.can_enter_jit(n=n, m=m, i=i)
                driver.jit_merge_point(n=n, m=m, i=i)
                if i >= 4:
                    i += 2
                i += 1

        self.meta_interp(loop, [1, 10], policy=JitPolicy(MyJitIface()))
        assert called == ["compile", "before_compile_bridge", "compile_bridge"]

    def test_resop_interface(self):
        driver = JitDriver(greens = [], reds = ['i'])

        def loop(i):
            while i > 0:
                driver.jit_merge_point(i=i)
                i -= 1

        def main():
            loop(1)
            op = jit_hooks.resop_new(rop.INT_ADD,
                                     [jit_hooks.boxint_new(3),
                                      jit_hooks.boxint_new(4)],
                                     jit_hooks.boxint_new(1))
            assert hlstr(jit_hooks.resop_getopname(op)) == 'int_add'
            assert jit_hooks.resop_getopnum(op) == rop.INT_ADD
            box = jit_hooks.resop_getarg(op, 0)
            assert jit_hooks.box_getint(box) == 3
            box2 = jit_hooks.box_clone(box)
            assert box2 != box
            assert jit_hooks.box_getint(box2) == 3
            assert not jit_hooks.box_isconst(box2)
            box3 = jit_hooks.box_constbox(box)
            assert jit_hooks.box_getint(box) == 3
            assert jit_hooks.box_isconst(box3)
            box4 = jit_hooks.box_nonconstbox(box)
            assert not jit_hooks.box_isconst(box4)
            box5 = jit_hooks.boxint_new(18)
            jit_hooks.resop_setarg(op, 0, box5)
            assert jit_hooks.resop_getarg(op, 0) == box5
            box6 = jit_hooks.resop_getresult(op)
            assert jit_hooks.box_getint(box6) == 1
            jit_hooks.resop_setresult(op, box5)
            assert jit_hooks.resop_getresult(op) == box5

        self.meta_interp(main, [])

    def test_get_stats(self):
        driver = JitDriver(greens = [], reds = ['i', 's'])

        def loop(i):
            s = 0
            while i > 0:
                driver.jit_merge_point(i=i, s=s)
                if i % 2:
                    s += 1
                i -= 1
                s+= 2
            return s

        def main():
            loop(30)
            assert jit_hooks.stats_get_counter_value(None,
                                           Counters.TOTAL_COMPILED_LOOPS) == 1
            assert jit_hooks.stats_get_counter_value(None,
                                           Counters.TOTAL_COMPILED_BRIDGES) == 1
            assert jit_hooks.stats_get_counter_value(None,
                                                     Counters.TRACING) == 2
            assert jit_hooks.stats_get_times_value(None, Counters.TRACING) >= 0

        self.meta_interp(main, [], ProfilerClass=Profiler)

    def test_get_stats_empty(self):
        driver = JitDriver(greens = [], reds = ['i'])
        def loop(i):
            while i > 0:
                driver.jit_merge_point(i=i)
                i -= 1
        def main():
            loop(30)
            assert jit_hooks.stats_get_counter_value(None,
                                           Counters.TOTAL_COMPILED_LOOPS) == 0
            assert jit_hooks.stats_get_times_value(None, Counters.TRACING) == 0
        self.meta_interp(main, [], ProfilerClass=EmptyProfiler)


class LLJitHookInterfaceTests(JitHookInterfaceTests):
    # use this for any backend, instead of the super class
    
    def test_ll_get_stats(self):
        driver = JitDriver(greens = [], reds = ['i', 's'])

        def loop(i):
            s = 0
            while i > 0:
                driver.jit_merge_point(i=i, s=s)
                if i % 2:
                    s += 1
                i -= 1
                s+= 2
            return s

        def main(b):
            jit_hooks.stats_set_debug(None, b)
            loop(30)
            l = jit_hooks.stats_get_loop_run_times(None)
            if b:
                assert len(l) == 4
                # completely specific test that would fail each time
                # we change anything major. for now it's 4
                # (loop, bridge, 2 entry points)
                assert l[0].type == 'e'
                assert l[0].number == 0
                assert l[0].counter == 4
                assert l[1].type == 'l'
                assert l[1].counter == 4
                assert l[2].type == 'l'
                assert l[2].counter == 23
                assert l[3].type == 'b'
                assert l[3].number == 4
                assert l[3].counter == 11
            else:
                assert len(l) == 0
        self.meta_interp(main, [True], ProfilerClass=Profiler)
        # this so far does not work because of the way setup_once is done,
        # but fine, it's only about untranslated version anyway
        #self.meta_interp(main, [False], ProfilerClass=Profiler)
        

class TestJitHookInterface(JitHookInterfaceTests, LLJitMixin):
    pass
