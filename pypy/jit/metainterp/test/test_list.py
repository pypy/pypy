import py
from pypy.rlib.jit import JitDriver
from pypy.jit.metainterp.test.support import LLJitMixin, OOJitMixin


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
    
    def test_arraycopy_simpleoptimize(self):
        def f():
            l = [1, 2, 3, 4]
            l2 = l[:]
            return l2[0] + l2[1] + l2[2] + l2[3]

        res = self.interp_operations(f, [], listops=True)
        assert res == 10

    def test_arraycopy_full(self):
        jitdriver = JitDriver(greens = [], reds = ['n'])
        def f(n):
            l = []
            l2 = []
            while n > 0:
                jitdriver.can_enter_jit(n=n)
                jitdriver.jit_merge_point(n=n)
                l = [1, 2, 3, n]
                l2 = l[:]
                n -= 1
            return l2[0] + l2[1] + l2[2] + l2[3]

        res = self.meta_interp(f, [5], listops=True)
        assert res == 7
        self.check_loops(call=0)

    def test_fold_getitem_1(self):
        jitdriver = JitDriver(greens = ['pc', 'n', 'l'], reds = ['total'])
        def f(n):
            l = [100, n, 300, n, 500]
            total = 0
            pc = n
            while True:
                jitdriver.can_enter_jit(l=l, pc=pc, n=n, total=total)
                jitdriver.jit_merge_point(l=l, pc=pc, n=n, total=total)
                total += l[pc]
                if total > 10000:
                    return total
                pc -= 1
                if pc < 0:
                    pc = n

        res = self.meta_interp(f, [4], listops=True)
        assert res == f(4)
        self.check_loops(call=0)

    def test_fold_getitem_2(self):
        jitdriver = JitDriver(greens = ['pc', 'n', 'l'], reds = ['total', 'x'])
        class X:
            pass
        def f(n):
            l = [100, n, 300, n, 500]
            total = 0
            x = X()
            x.pc = n
            while True:
                pc = x.pc
                jitdriver.can_enter_jit(l=l, pc=pc, n=n, total=total, x=x)
                jitdriver.jit_merge_point(l=l, pc=pc, n=n, total=total, x=x)
                x.pc = pc
                total += l[x.pc]
                if total > 10000:
                    return total
                x.pc -= 1
                if x.pc < 0:
                    x.pc = n

        res = self.meta_interp(f, [4], listops=True)
        assert res == f(4)
        self.check_loops(call=0, getfield_gc=0)

    def test_fold_indexerror(self):
        jitdriver = JitDriver(greens = [], reds = ['total', 'n', 'lst'])
        def f(n):
            lst = []
            total = 0
            while n > 0:
                jitdriver.can_enter_jit(lst=lst, n=n, total=total)
                jitdriver.jit_merge_point(lst=lst, n=n, total=total)
                lst.append(n)
                try:
                    total += lst[n]
                except IndexError:
                    total += 1000
                n -= 1
            return total

        res = self.meta_interp(f, [15], listops=True)
        assert res == f(15)
        self.check_loops(guard_exception=0)

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
        self.check_loops(getfield_gc=1, everywhere=True)
