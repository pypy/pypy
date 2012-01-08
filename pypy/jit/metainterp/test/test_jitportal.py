
from pypy.rlib.jit import JitDriver, JitPortal
from pypy.rlib import jit_hooks
from pypy.jit.metainterp.test.support import LLJitMixin
from pypy.jit.codewriter.policy import JitPolicy
from pypy.jit.metainterp.jitprof import ABORT_FORCE_QUASIIMMUT
from pypy.jit.metainterp.resoperation import rop

class TestJitPortal(LLJitMixin):
    def test_abort_quasi_immut(self):
        reasons = []
        
        class MyJitPortal(JitPortal):
            def on_abort(self, reason, jitdriver, greenkey):
                assert jitdriver is myjitdriver
                assert len(greenkey) == 1
                reasons.append(reason)

        portal = MyJitPortal()

        myjitdriver = JitDriver(greens=['foo'], reds=['x', 'total'])

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
        res = self.meta_interp(f, [100, 7], policy=JitPolicy(portal))
        assert res == 721
        assert reasons == [ABORT_FORCE_QUASIIMMUT] * 2

    def test_on_compile(self):
        called = []
        
        class MyJitPortal(JitPortal):
            def after_compile(self, jitdriver, logger, looptoken, operations,
                              type, greenkey, ops_offset, asmaddr, asmlen):
                assert asmaddr == 0
                assert asmlen == 0
                called.append(("compile", greenkey[1].getint(),
                               greenkey[0].getint(), type))

            def before_compile(self, jitdriver, logger, looptoken, oeprations,
                               type, greenkey):
                called.append(("optimize", greenkey[1].getint(),
                               greenkey[0].getint(), type))

            def before_optimize(self, jitdriver, logger, looptoken, oeprations,
                               type, greenkey):
                called.append(("trace", greenkey[1].getint(),
                               greenkey[0].getint(), type))

        portal = MyJitPortal()

        driver = JitDriver(greens = ['n', 'm'], reds = ['i'])

        def loop(n, m):
            i = 0
            while i < n + m:
                driver.can_enter_jit(n=n, m=m, i=i)
                driver.jit_merge_point(n=n, m=m, i=i)
                i += 1

        self.meta_interp(loop, [1, 4], policy=JitPolicy(portal))
        assert called == [#("trace", 4, 1, "loop"),
                          ("optimize", 4, 1, "loop"),
                          ("compile", 4, 1, "loop")]
        self.meta_interp(loop, [2, 4], policy=JitPolicy(portal))
        assert called == [#("trace", 4, 1, "loop"),
                          ("optimize", 4, 1, "loop"),
                          ("compile", 4, 1, "loop"),
                          #("trace", 4, 2, "loop"),
                          ("optimize", 4, 2, "loop"),
                          ("compile", 4, 2, "loop")]

    def test_on_compile_bridge(self):
        called = []
        
        class MyJitPortal(JitPortal):
            def after_compile(self, jitdriver, logger, looptoken, operations,
                           type, greenkey, ops_offset, asmaddr, asmlen):
                assert asmaddr == 0
                assert asmlen == 0
                called.append("compile")

            def after_compile_bridge(self, jitdriver, logger, orig_token,
                                     operations, n, ops_offset, asmstart, asmlen):
                called.append("compile_bridge")

            def before_compile_bridge(self, jitdriver, logger, orig_token,
                                     operations, n):
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

        self.meta_interp(loop, [1, 10], policy=JitPolicy(MyJitPortal()))
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
            return jit_hooks.resop_opnum(op)

        res = self.meta_interp(main, [])
        assert res == rop.INT_ADD
