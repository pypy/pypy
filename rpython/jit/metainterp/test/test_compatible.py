from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.rlib import jit
from rpython.rtyper.lltypesystem import lltype, rffi


class TestCompatible(LLJitMixin):
    def test_simple(self):
        S = lltype.GcStruct('S', ('x', lltype.Signed))
        p1 = lltype.malloc(S)
        p1.x = 5

        p2 = lltype.malloc(S)
        p2.x = 5

        p3 = lltype.malloc(S)
        p3.x = 6
        driver = jit.JitDriver(greens = [], reds = ['n', 'x'])
        @jit.elidable_compatible()
        def g(s):
            return s.x

        def f(n, x):
            while n > 0:
                driver.can_enter_jit(n=n, x=x)
                driver.jit_merge_point(n=n, x=x)
                n -= g(x)

        def main():
            f(100, p1)
            f(100, p2)
            f(100, p3)

        self.meta_interp(main, [])
        # XXX check number of bridges

