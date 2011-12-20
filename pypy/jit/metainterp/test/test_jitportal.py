
from pypy.rlib.jit import JitDriver, JitPortal
from pypy.jit.metainterp.test.support import LLJitMixin
from pypy.jit.codewriter.policy import PortalPolicy

class TestJitPortal(LLJitMixin):
    def test_abort_quasi_immut(self):
        class MyJitPortal(JitPortal):
            def abort(self, *args):
                xxxx

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
        res = self.meta_interp(f, [100, 7], policy=PortalPolicy(portal))
        assert res == 721
        
