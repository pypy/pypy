import py
from pypy.rlib.jit import JitDriver, OPTIMIZER_SIMPLE
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin


class DelTests:

    def test_del_keep_obj(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'x'])
        class Foo:
            def __del__(self):
                pass
        def f(n):
            x = None
            while n > 0:
                myjitdriver.can_enter_jit(x=x, n=n)
                myjitdriver.jit_merge_point(x=x, n=n)
                x = Foo()
                Foo()
                n -= 1
            return 42
        self.meta_interp(f, [20])
        self.check_loops({'call': 2,      # calls to a helper function
                          'guard_no_exception': 2,    # follows the calls
                          'int_sub': 1,
                          'int_gt': 1,
                          'guard_true': 1,
                          'jump': 1})

    def test_class_of_allocated(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'x'])
        class Foo:
            def __del__(self):
                pass
            def f(self):
                return self.meth()
        class X(Foo):
            def meth(self):
                return 456
        class Y(Foo):
            def meth(self):
                return 123
        def f(n):
            x = None
            while n > 0:
                myjitdriver.can_enter_jit(x=x, n=n)
                myjitdriver.jit_merge_point(x=x, n=n)
                x = X()
                y = Y()
                assert x.f() == 456
                assert y.f() == 123
                n -= 1
            return 42
        res = self.meta_interp(f, [20])
        assert res == 42

    def test_instantiate_with_or_without_del(self):
        import gc
        mydriver = JitDriver(reds = ['n', 'x'], greens = [])
        class Base: pass
        class A(Base): foo = 72
        class B(Base):
            foo = 8
            def __del__(self):
                pass
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
            return 1
        res = self.meta_interp(f, [20], optimizer=OPTIMIZER_SIMPLE)
        assert res == 1
        self.check_loops(call=1)   # for the case B(), but not for the case A()


class TestLLtype(DelTests, LLJitMixin):
    def test_signal_action(self):
        from pypy.module.signal.interp_signal import SignalActionFlag
        action = SignalActionFlag()
        #
        myjitdriver = JitDriver(greens = [], reds = ['n', 'x'])
        class X:
            pass
        #
        def f(n):
            x = X()
            while n > 0:
                myjitdriver.can_enter_jit(n=n, x=x)
                myjitdriver.jit_merge_point(n=n, x=x)
                x.foo = n
                n -= 1
                if action.get() != 0:
                    break
                action.set(0)
            return 42
        self.meta_interp(f, [20])
        self.check_loops(getfield_raw=1, call=0, call_pure=0)

class TestOOtype(DelTests, OOJitMixin):
    def setup_class(cls):
        py.test.skip("XXX dels are not implemented in the"
                     " static CLI or JVM backend")
