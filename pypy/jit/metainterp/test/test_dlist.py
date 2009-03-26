
import py
from pypy.rlib.jit import JitDriver
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin
py.test.skip("Disabled")

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

        res = self.meta_interp(f, [10], listops=True)
        assert res == f(10)        
        self.check_loops(getarrayitem_gc=0, setarrayitem_gc=1)
#                         XXX fix codewriter
#                         guard_exception=0,
#                         guard_no_exception=1)

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

        res = self.meta_interp(f, [10], listops=True)
        assert res == f(10)
        self.check_loops(setarrayitem_gc=2, getarrayitem_gc=0)

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

        res = self.meta_interp(f, [10], listops=True)
        assert res == f(10)
        self.check_loops(setarrayitem_gc=3, getarrayitem_gc=0)

    def test_list_of_ptrs(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'l'])
        class A(object):
            def __init__(self, x):
                self.x = x

        def f(n):
            l = [A(3)]
            while n > 0:
                myjitdriver.can_enter_jit(n=n, l=l)
                myjitdriver.jit_merge_point(n=n, l=l)
                x = l[0].x + 1
                l[0] = A(x)
                n -= 1
            return l[0].x

        res = self.meta_interp(f, [10], listops=True)
        assert res == f(10)
        self.check_loops(setarrayitem_gc=1, getarrayitem_gc=0,
                         new_with_vtable=1) # A should escape

    def test_list_checklength(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'l'])

        def f(n, a):
            l = [0] * a
            while n > 0:
                myjitdriver.can_enter_jit(n=n, l=l)
                myjitdriver.jit_merge_point(n=n, l=l)
                if len(l) < 3:
                    return 42
                l[0] = n
                n -= 1
            return l[0]

        res = self.meta_interp(f, [10, 13], listops=True)
        assert res == f(10, 13)
        self.check_loops(setarrayitem_gc=1, arraylen_gc=1)

    def test_list_checklength_run(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'l'])

        def f(n, a):
            l = [0] * a
            while n > 0:
                myjitdriver.can_enter_jit(n=n, l=l)
                myjitdriver.jit_merge_point(n=n, l=l)
                if len(l) > n:
                    return 42
                l[0] = n
                n -= 1
            return l[0]

        res = self.meta_interp(f, [50, 13], listops=True)
        assert res == 42
        self.check_loops(setarrayitem_gc=1, arraylen_gc=1)

    def test_checklength_cannot_go_away(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'l'])

        def f(n):
            l = [0] * n
            while n > 0:
                myjitdriver.can_enter_jit(n=n, l=l)
                myjitdriver.jit_merge_point(n=n, l=l)
                if len(l) < 3:
                    return len(l)
                l = [0] * n
                n -= 1
            return 0

        res = self.meta_interp(f, [10], listops=True)
        assert res == 2
        self.check_loops(arraylen_gc=1)

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
