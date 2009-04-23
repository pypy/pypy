import py
from pypy.jit.metainterp.policy import StopAtXPolicy
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin
from pypy.rlib.jit import JitDriver

class ListTests:

    def test_basic_list(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'lst'])
        def f(n):
            lst = []
            while n > 0:
                myjitdriver.can_enter_jit(n=n, lst=lst)
                myjitdriver.jit_merge_point(n=n, lst=lst)
                lst.append(n)
                n -= len(lst)
            return len(lst)
        res = self.meta_interp(f, [42], listops=True)
        assert res == 9

    def test_list_operations(self):
        class FooBar:
            def __init__(self, z):
                self.z = z
        def f(n):
            lst = [41, 42]
            lst[0] = len(lst)     # [2, 42]
            lst.append(lst[1])    # [2, 42, 42]
            m = lst.pop()         # 42
            m += lst.pop(0)       # 44
            lst2 = [FooBar(3)]
            lst2.append(FooBar(5))
            m += lst2.pop().z     # 49
            return m
        res = self.interp_operations(f, [11], listops=True)
        assert res == 49

    def test_lazy_getitem_1(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'lst'])
        def f(n):
            lst = [0]
            while n > 0:
                myjitdriver.can_enter_jit(n=n, lst=lst)
                myjitdriver.jit_merge_point(n=n, lst=lst)
                lst[0] += 2
                n -= 1
            return lst[0]
        res = self.meta_interp(f, [21], listops=True)
        assert res == 42
        # no more list operations in the loop
        py.test.skip("not a ModifiedList yet")
        self.check_loops(call=0)

    def test_lazy_getitem_2(self):
        py.test.skip("BUG!")
        class Escape:
            pass
        escape = Escape()
        def g():
            return escape.lst[0]
        def f(n):
            lst = [0]
            escape.lst = lst
            while n > 0:
                lst[0] += 2
                n -= g()
            return lst[0]
        res = self.meta_interp(f, [50], policy=StopAtXPolicy(g))
        assert res == f(50)
        # the list operations stay in the loop
        self.check_loops(call=3)

    def test_lazy_getitem_3(self):
        py.test.skip("in-progress")
        def f(n):
            lst = [[0]]
            while n > 0:
                lst[0][0] = lst[0][0] + 2
                n -= 1
            return lst[0][0]
        res = self.meta_interp(f, [21])
        assert res == 42
        # two levels of list operations removed from the loop
        self.check_loops(call=0)

    def test_lazy_getitem_4(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'lst'])
        def f(n):
            lst = [0]
            while n > 0:
                myjitdriver.can_enter_jit(n=n, lst=lst)
                myjitdriver.jit_merge_point(n=n, lst=lst)
                lst[-1] += 2
                n -= 1
            return lst[0]
        res = self.meta_interp(f, [21], listops=True)
        assert res == 42
        py.test.skip("not virtualized away so far")

class TestOOtype(ListTests, OOJitMixin):
   pass

class TestLLtype(ListTests, LLJitMixin):
    pass
