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
        self.meta_interp(f, [20])
        self.check_loops({'call': 2,      # calls to a helper function
                          'guard_no_exception': 2,    # follows the calls
                          'int_sub': 1,
                          'int_gt': 1,
                          'guard_true': 1,
                          'jump': 1})


class TestLLtype(DelTests, LLJitMixin):
    pass

class TestOOtype(DelTests, OOJitMixin):
    def setup_class(cls):
        py.test.skip("XXX dels are not implemented in the"
                     " static CLI or JVM backend")
