import py
from pypy.rlib.jit import JitDriver
from pypy.jit.metainterp.policy import StopAtXPolicy
from pypy.jit.metainterp.test.test_basic import LLJitMixin


class Base:
    pass
class A(Base):
    def decr(self, n):
        return n - 1
class B(Base):
    def __init__(self, x):
        self.x = x
    def decr(self, n):
        return self.x - 3


class InverseGuardTests:

    def test_bug1(self):
        py.test.skip("BOOM")
        myjitdriver = JitDriver(greens = [], reds = ['node', 'n'])
        def extern(n):
            if n <= 21:
                return B(n)
            else:
                return A()
        def f(n):
            node = A()
            while n >= 0:
                myjitdriver.can_enter_jit(node=node, n=n)
                myjitdriver.jit_merge_point(node=node, n=n)
                n = node.decr(n)
                node = extern(n)
            return n
        res = self.meta_interp(f, [40], policy=StopAtXPolicy(extern))
        assert res == f(40)


class TestLLtype(InverseGuardTests, LLJitMixin):
    pass
