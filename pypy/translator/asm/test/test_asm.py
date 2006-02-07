from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.backendopt.all import backend_optimizations
from pypy.rpython.rarithmetic import ovfcheck
from pypy.translator.asm import genasm
from pypy import conftest
import py
import os

class TestAsm(object):

    processor = 'virt'

    def getcompiled(self, func, view=False):
        t = TranslationContext(simplifying=True)
        # builds starting-types from func_defs
        argstypelist = []
        if func.func_defaults is None:
            assert func.func_code.co_argcount == 0
            argtypes = []
        else:
            assert len(func.func_defaults) == func.func_code.co_argcount
            argtypes = list(func.func_defaults)
        a = t.buildannotator()
        a.build_types(func, argtypes)
        a.simplify()
        r = t.buildrtyper()
        r.specialize()
        t.checkgraphs()
        
        backend_optimizations(t)
        if view or conftest.option.view:
            t.view()
        graph = graphof(t, func)
        return genasm.genasm(graph, self.processor)

    def dont_test_trivial(self):
        def testfn():
            return None
        f = self.getcompiled(testfn)
        assert f() == None

    def test_int_add(self):
        def testfn(x=int, y=int):
            z = 1 + x
            if z > 0:
                return x + y + z
            else:
                return x + y - 42
        f = self.getcompiled(testfn)#, view=True)

        assert f(-2, 3) == testfn(-2, 3)
        assert f(2, 5) == testfn(2, 5)

    def test_loop(self):
        def testfn(lim=int):
            r = 0
            i = 0
            while i < lim:
                r += i*i
                i += 1
            return r
        f = self.getcompiled(testfn)#, view=True)

        assert f(0) == testfn(0)
        assert f(10) == testfn(10)
        assert f(100) == testfn(100)
        assert f(1000) == testfn(1000)

    def test_factor(self):
        def factor(n=int):
            i = 2
            while i < n:
                if n % i == 0:
                    return i
                i += 1
            return i
        f = self.getcompiled(factor)

        assert f(25) == 5
        assert f(27) == 3
        assert f(17*13) == 13
        assert f(29) == 29

    def test_from_psyco(self):
        def f1(n=int):
            "Arbitrary test function."
            i = 0
            x = 1
            while i<n:
                j = 0
                while j<=i:
                    j = j + 1
                    x = x + (i&j)
                i = i + 1
            return x

        f = self.getcompiled(f1)
        assert f(10) == f1(10)

    def test_comparisons(self):
        def f(x=int):
            if x == 0:
                return 0
            elif x > 10:
                return 10
            elif x >= 5:
                return 5
            elif x < -10:
                return -10
            elif x <= -5:
                return -5
            elif x != 1:
                return 1
            else:
                return x
        g = self.getcompiled(f)
        for i in range(-20, 20):
            assert g(i) == f(i)

    def dont_test_overflow(self):
        def f(x=int, y=int):
            try:
                return ovfcheck(x*y)
            except OverflowError:
                return 0
        g = self.getcompiled(f, view=True)
        assert f(3, 4) == g(3, 4)
        big = 1000000000
        assert f(big, big) == g(big, big)
        
## class TestAsmAfterAllocation(TestAsm):

##     processor = 'virtfinite'


class TestAsmPPC(TestAsm):

    processor = 'ppc'

    def setup_class(cls):
        if not hasattr(os, "uname") or os.uname()[-1] != 'Power Macintosh':
            py.test.skip('asm generation only on PPC')


