import py
from pypy.rlib.jit import JitDriver
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


class TestLLtype(DelTests, LLJitMixin):
    pass

class TestOOtype(DelTests, OOJitMixin):
    def setup_class(cls):
        py.test.skip("XXX dels are not implemented in the"
                     " static CLI or JVM backend")
