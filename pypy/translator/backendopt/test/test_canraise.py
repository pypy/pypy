from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.backendopt.canraise import RaiseAnalyzer
from pypy.translator.backendopt.all import backend_optimizations
from pypy.rpython.test.tool import LLRtypeMixin, OORtypeMixin
from pypy.conftest import option

class BaseTestCanRaise(object):
    type_system = None

    def translate(self, func, sig):
        t = TranslationContext()
        t.buildannotator().build_types(func, sig)
        t.buildrtyper(type_system=self.type_system).specialize()
        if option.view:
            t.view()
        return t, RaiseAnalyzer(t)


    def test_can_raise_simple(self):
        def g(x):
            return True

        def f(x):
            return g(x - 1)
        t, ra = self.translate(f, [int])
        fgraph = graphof(t, f)
        result = ra.can_raise(fgraph.startblock.operations[0])
        assert not result

    def test_can_raise_recursive(self):
        from pypy.translator.transform import insert_ll_stackcheck
        def g(x):
            return f(x)

        def f(x):
            if x:
                return g(x - 1)
            return 1
        t, ra = self.translate(f, [int])
        insert_ll_stackcheck(t)
        ggraph = graphof(t, g)
        result = ra.can_raise(ggraph.startblock.operations[-1])
        assert result # due to stack check every recursive function can raise

    def test_can_raise_exception(self):
        def g():
            raise ValueError
        def f():
            return g()
        t, ra = self.translate(f, [])
        fgraph = graphof(t, f)
        result = ra.can_raise(fgraph.startblock.operations[0])
        assert result

    def test_indirect_call(self):
        def g1():
            raise ValueError
        def g2():
            return 2
        def f(x):
            if x:
                g = g1
            else:
                g = g2
            return g()
        def h(x):
            return f(x)
        t, ra = self.translate(h, [int])
        hgraph = graphof(t, h)
        result = ra.can_raise(hgraph.startblock.operations[0])
        assert result

    def test_instantiate(self):
        # instantiate is interesting, because it leads to one of the few cases of
        # an indirect call without a list of graphs
        from pypy.rlib.objectmodel import instantiate
        class A:
            pass 
        class B(A):
            pass
        def g(x):
            if x:
                C = A
            else:
                C = B
            a = instantiate(C)
        def f(x):
            return g(x)
        t, ra = self.translate(f, [int])
        fgraph = graphof(t, f)
        result = ra.can_raise(fgraph.startblock.operations[0])
        assert result

class TestLLType(LLRtypeMixin, BaseTestCanRaise):
    def test_llexternal(self):
        from pypy.rpython.lltypesystem.rffi import llexternal
        from pypy.rpython.lltypesystem import lltype
        z = llexternal('z', [lltype.Signed], lltype.Signed)
        def f(x):
            return z(x)
        t, ra = self.translate(f, [int])
        fgraph = graphof(t, f)
        backend_optimizations(t)
        assert fgraph.startblock.operations[0].opname == 'direct_call'

        result = ra.can_raise(fgraph.startblock.operations[0])
        assert not result

        z = llexternal('z', [lltype.Signed], lltype.Signed, canraise=True)
        def g(x):
            return z(x)
        t, ra = self.translate(g, [int])
        ggraph = graphof(t, g)

        assert ggraph.startblock.operations[0].opname == 'direct_call'

        result = ra.can_raise(ggraph.startblock.operations[0])
        assert result


class TestOOType(OORtypeMixin, BaseTestCanRaise):
    pass


