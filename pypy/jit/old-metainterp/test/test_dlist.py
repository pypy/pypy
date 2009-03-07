
import py
py.test.skip("turned off for now")
from pypy.rlib.jit import JitDriver
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin

class ListTests:
    def test_basic(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'l'])
        def f(n):
            l = [0]
            while n > 0:
                myjitdriver.can_enter_jit(n=n, l=l)
                myjitdriver.jit_merge_point(n=n, l=l)
                x = l[0]
                l[0] = x + 1
                n -= 1
            return l[0]

        res = self.meta_interp(f, [10])
        assert res == f(10)        
        self.check_loops(getitem=0, setitem=1, guard_exception=0,
                         guard_no_exception=1)

    def test_list_escapes(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'l'])
        def f(n):
            l = [0] * (n + 1)
            while n > 0:
                myjitdriver.can_enter_jit(n=n, l=l)
                myjitdriver.jit_merge_point(n=n, l=l)
                x = l[0]
                l[0] = x + 1
                l[n] = n
                n -= 1
            return l[3]

        res = self.meta_interp(f, [10])
        assert res == f(10)
        self.check_loops(setitem=2, getitem=0)

    def test_list_escapes_but_getitem_goes(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'l'])
        def f(n):
            l = [0] * (n + 1)
            while n > 0:
                myjitdriver.can_enter_jit(n=n, l=l)
                myjitdriver.jit_merge_point(n=n, l=l)
                x = l[0]
                l[0] = x + 1
                l[n] = n
                x = l[2]
                y = l[1] + l[2]
                l[1] = x + y
                n -= 1
            return l[3]

        res = self.meta_interp(f, [10])
        assert res == f(10)
        self.check_loops(setitem=3, getitem=0)

    def test_list_indexerror(self):
        # this is an example where IndexError is raised before
        # even getting to the JIT
        py.test.skip("I suspect bug somewhere outside of the JIT")
        myjitdriver = JitDriver(greens = [], reds = ['n', 'l'])
        def f(n):
            l = [0]
            while n > 0:
                myjitdriver.can_enter_jit(n=n, l=l)
                myjitdriver.jit_merge_point(n=n, l=l)
                l[n] = n
                n -= 1
            return l[3]

        def g(n):
            try:
                f(n)
                return 0
            except IndexError:
                return 42

        res = self.meta_interp(g, [10])
        assert res == 42
        self.check_loops(setitem=2)

class TestLLtype(ListTests, LLJitMixin):
    pass
