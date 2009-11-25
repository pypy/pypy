import py
from pypy.rlib.jit import JitDriver
from pypy.jit.metainterp.policy import StopAtXPolicy
from pypy.rpython.ootypesystem import ootype
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin


class ListTests:

    def check_all_virtualized(self):
        self.check_loops(new_array=0, setarrayitem_gc=0, getarrayitem_gc=0,
                         arraylen_gc=0)

    def test_simple_array(self):
        jitdriver = JitDriver(greens = [], reds = ['n'])
        def f(n):
            while n > 0:
                jitdriver.can_enter_jit(n=n)
                jitdriver.jit_merge_point(n=n)
                lst = [n]
                n = lst[0] - 1
            return n
        res = self.meta_interp(f, [10], listops=True)
        assert res == 0
        self.check_loops(int_sub=1)
        self.check_all_virtualized()

    def test_list_pass_around(self):
        jitdriver = JitDriver(greens = [], reds = ['n', 'l'])
        def f(n):
            l = [3]
            while n > 0:
                jitdriver.can_enter_jit(n=n, l=l)
                jitdriver.jit_merge_point(n=n, l=l)
                x = l[0]
                l = [x + 1]
                n -= 1
            return l[0]
        
        res = self.meta_interp(f, [10], listops=True)
        assert res == f(10)
        self.check_all_virtualized()

    def test_cannot_be_virtual(self):
        jitdriver = JitDriver(greens = [], reds = ['n', 'l'])
        def f(n):
            l = [3] * 100
            while n > 0:
                jitdriver.can_enter_jit(n=n, l=l)
                jitdriver.jit_merge_point(n=n, l=l)
                x = l[n]
                l = [3] * 100
                l[3] = x
                l[3] = x + 1
                n -= 1
            return l[0]

        res = self.meta_interp(f, [10], listops=True)
        assert res == f(10)
        # one setitem should be gone by now
        self.check_loops(call=1, setarrayitem_gc=2, getarrayitem_gc=1)

    def test_ll_fixed_setitem_fast(self):
        jitdriver = JitDriver(greens = [], reds = ['n', 'l'])
        
        def f(n):
            l = [1, 2, 3]

            while n > 0:
                jitdriver.can_enter_jit(n=n, l=l)
                jitdriver.jit_merge_point(n=n, l=l)
                l = l[:]
                n -= 1
            return l[0]

        res = self.meta_interp(f, [10], listops=True)
        assert res == 1
        py.test.skip("Constant propagation of length missing")
        self.check_loops(setarrayitem_gc=0, call=0)

    def test_vlist_with_default_read(self):
        jitdriver = JitDriver(greens = [], reds = ['n'])
        def f(n):
            l = [1] * 20
            while n > 0:
                jitdriver.can_enter_jit(n=n)
                jitdriver.jit_merge_point(n=n)
                l = [0] * 20
                l[3] = 5
                x = l[-17] + l[5] # that should be zero
                if n < 3:
                    return x
                n -= 1
            return l[0]

        res = self.meta_interp(f, [10], listops=True)
        assert res == f(10)
        self.check_loops(setarrayitem_gc=0, getarrayitem_gc=0, call=0)

    def test_vlist_alloc_and_set(self):
        # the check_loops fails, because [non-null] * n is not supported yet
        # (it is implemented as a residual call)
        jitdriver = JitDriver(greens = [], reds = ['n'])
        def f(n):
            l = [1] * 20
            while n > 0:
                jitdriver.can_enter_jit(n=n)
                jitdriver.jit_merge_point(n=n)
                l = [1] * 20
                l[3] = 5
                x = l[-17] + l[5] - 1
                if n < 3:
                    return x
                n -= 1
            return l[0]

        res = self.meta_interp(f, [10], listops=True)
        assert res == f(10)
        py.test.skip("'[non-null] * n' gives a residual call so far")
        self.check_loops(setarrayitem_gc=0, getarrayitem_gc=0, call=0)
        
    def test_append_pop(self):
        py.test.skip("unsupported")
        jitdriver = JitDriver(greens = [], reds = ['n'])
        def f(n):
            while n > 0:
                jitdriver.can_enter_jit(n=n)
                jitdriver.jit_merge_point(n=n)
                lst = []
                lst.append(5)
                lst.append(n)
                lst[0] -= len(lst)
                three = lst[0]
                n = lst.pop() - three
            return n
        res = self.meta_interp(f, [31])
        assert res == -2
        self.check_all_virtualized()

    def test_insert(self):
        py.test.skip("unsupported")
        jitdriver = JitDriver(greens = [], reds = ['n'])
        def f(n):
            while n > 0:
                jitdriver.can_enter_jit(n=n)
                jitdriver.jit_merge_point(n=n)
                lst = [1, 2, 3]
                lst.insert(0, n)
                n = lst[0] - 1
                lst.pop()
                # last pop is needed, otherwise it won't work
            return n
        res = self.meta_interp(f, [33])
        assert res == f(33)
        self.check_all_virtualized()

    def test_nonzero(self):
        py.test.skip("unsupported")
        jitdriver = JitDriver(greens = [], reds = ['n'])
        def f(n):
            while n > 0:
                jitdriver.can_enter_jit(n=n)
                jitdriver.jit_merge_point(n=n)
                lst = [1, 2, 3]
                lst.insert(0, n)
                # nonzero should go away
                if not lst:
                    return -33
                n = lst[0] - 1
                lst.pop()
                # last pop is needed, otherwise it won't work
            return n
        res = self.meta_interp(f, [33])
        assert res == f(33)
        self.check_all_virtualized()
        self.check_loops(listnonzero=0, guard_true=1, guard_false=0)

    def test_append_pop_rebuild(self):
        py.test.skip("unsupported")
        jitdriver = JitDriver(greens = [], reds = ['n'])
        def f(n):
            while n > 0:
                jitdriver.can_enter_jit(n=n)
                jitdriver.jit_merge_point(n=n)
                lst = []
                lst.append(5)
                lst.append(n)
                lst[0] -= len(lst)
                three = lst[0]
                n = lst.pop() - three
                if n == 2:
                    return n + lst.pop()
            return n
        res = self.meta_interp(f, [31])
        assert res == -2
        self.check_all_virtualized()

    def test_list_escapes(self):
        py.test.skip("unsupported")
        jitdriver = JitDriver(greens = [], reds = ['n'])
        def f(n):
            while True:
                jitdriver.can_enter_jit(n=n)
                jitdriver.jit_merge_point(n=n)
                lst = []
                lst.append(n)
                n = lst.pop() - 3
                if n < 0:
                    return len(lst)
        res = self.meta_interp(f, [31])
        assert res == 0
        self.check_all_virtualized()

    def test_list_reenters(self):
        py.test.skip("unsupported")
        jitdriver = JitDriver(greens = [], reds = ['n'])
        def f(n):
            while n > 0:
                jitdriver.can_enter_jit(n=n)
                jitdriver.jit_merge_point(n=n)
                lst = []
                lst.append(n)
                if n < 10:
                    lst[-1] = n-1
                n = lst.pop() - 3
            return n
        res = self.meta_interp(f, [31])
        assert res == -1
        self.check_all_virtualized()

    def test_cannot_merge(self):
        py.test.skip("unsupported")
        jitdriver = JitDriver(greens = [], reds = ['n'])
        def f(n):
            while n > 0:
                jitdriver.can_enter_jit(n=n)
                jitdriver.jit_merge_point(n=n)
                lst = []
                if n < 20:
                    lst.append(n-3)
                if n > 5:
                    lst.append(n-4)
                n = lst.pop()
            return n
        res = self.meta_interp(f, [30])
        assert res == -1
        self.check_all_virtualized()

    def test_list_escapes(self):
        py.test.skip("unsupported")
        jitdriver = JitDriver(greens = [], reds = ['n'])
        def g(l):
            pass
        
        def f(n):
            while n > 0:
                jitdriver.can_enter_jit(n=n)
                jitdriver.jit_merge_point(n=n)
                l = []
                l.append(3)
                g(l)
                n -= 1
            return n
        res = self.meta_interp(f, [30], policy=StopAtXPolicy(g))
        assert res == 0
        self.check_loops(append=1)

    def test_list_escapes_various_ops(self):
        py.test.skip("unsupported")
        jitdriver = JitDriver(greens = [], reds = ['n'])
        def g(l):
            pass
        
        def f(n):
            while n > 0:
                jitdriver.can_enter_jit(n=n)
                jitdriver.jit_merge_point(n=n)
                l = []
                l.append(3)
                l.append(1)
                n -= l.pop()
                n -= l[0]
                if l:
                    g(l)
                n -= 1
            return n
        res = self.meta_interp(f, [30], policy=StopAtXPolicy(g))
        assert res == 0
        self.check_loops(append=2)

    def test_list_escapes_find_nodes(self):
        py.test.skip("unsupported")
        jitdriver = JitDriver(greens = [], reds = ['n'])
        def g(l):
            pass
        
        def f(n):
            while n > 0:
                jitdriver.can_enter_jit(n=n)
                jitdriver.jit_merge_point(n=n)
                l = [0] * n
                l.append(3)
                l.append(1)
                n -= l.pop()
                n -= l[-1]
                if l:
                    g(l)
                n -= 1
            return n
        res = self.meta_interp(f, [30], policy=StopAtXPolicy(g))
        assert res == 0
        self.check_loops(append=2)

    def test_stuff_escapes_via_setitem(self):
        py.test.skip("unsupported")
        jitdriver = JitDriver(greens = [], reds = ['n', 'l'])
        class Stuff(object):
            def __init__(self, x):
                self.x = x
        
        def f(n):
            l = [None]
            while n > 0:
                jitdriver.can_enter_jit(n=n, l=l)
                jitdriver.jit_merge_point(n=n, l=l)
                s = Stuff(3)
                l.append(s)
                n -= l[0].x
            return n
        res = self.meta_interp(f, [30])
        assert res == 0
        self.check_loops(append=1)

    def test_virtual_escaping_via_list(self):
        py.test.skip("unsupported")
        jitdriver = JitDriver(greens = [], reds = ['n', 'l'])
        class Stuff(object):
            def __init__(self, x):
                self.x = x

        def f(n):
            l = [Stuff(n-i) for i in range(n)]

            while n > 0:
                jitdriver.can_enter_jit(n=n, l=l)
                jitdriver.jit_merge_point(n=n, l=l)
                s = l.pop()
                n -= s.x

        res = self.meta_interp(f, [20])
        assert res == f(20)
        self.check_loops(pop=1, getfield_gc=1)

    def test_extend(self):
        py.test.skip("XXX")
        def f(n):
            while n > 0:
                lst = [5, 2]
                lst.extend([6, 7, n - 10])
                n = lst.pop()
            return n
        res = self.meta_interp(f, [33], exceptions=False)
        assert res == -7
        self.check_all_virtualized()

    def test_single_list(self):
        py.test.skip("in-progress")
        def f(n):
            lst = [n] * n
            while n > 0:
                n = lst.pop()
                lst.append(n - 10)
            a = lst.pop()
            b = lst.pop()
            return a * b
        res = self.meta_interp(f, [37], exceptions=False)
        assert res == -13 * 37
        self.check_all_virtualized()



class TestOOtype(ListTests, OOJitMixin):
    pass

class TestLLtype(ListTests, LLJitMixin):
    def test_listops_dont_invalidate_caches(self):
        class A(object):
            pass
        jitdriver = JitDriver(greens = [], reds = ['n', 'a', 'lst'])
        def f(n):
            a = A()
            a.x = 1
            if n < 1091212:
                a.x = 2 # fool the annotator
            lst = [n * 5, n * 10, n * 20]
            while n > 0:
                jitdriver.can_enter_jit(n=n, a=a, lst=lst)
                jitdriver.jit_merge_point(n=n, a=a, lst=lst)
                n += a.x
                n = lst.pop()
                lst.append(n - 10 + a.x)
                if a.x in lst:
                    pass
                a.x = a.x + 1 - 1
            a = lst.pop()
            b = lst.pop()
            return a * b
        res = self.meta_interp(f, [37])
        assert res == f(37)
        self.check_loops(getfield_gc=1)
