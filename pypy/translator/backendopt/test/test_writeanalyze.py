import py
from pypy.rpython.lltypesystem import lltype
from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.simplify import get_funcobj
from pypy.translator.backendopt.writeanalyze import WriteAnalyzer, top_set
from pypy.translator.backendopt.all import backend_optimizations
from pypy.conftest import option


class TestCanRaise(object):

    def translate(self, func, sig):
        t = TranslationContext()
        t.buildannotator().build_types(func, sig)
        t.buildrtyper().specialize()
        if option.view:
            t.view()
        return t, WriteAnalyzer(t)


    def test_writes_simple(self):
        def g(x):
            return True

        def f(x):
            return g(x - 1)
        t, wa = self.translate(f, [int])
        fgraph = graphof(t, f)
        result = wa.analyze(fgraph.startblock.operations[0])
        assert not result

    def test_writes_recursive(self):
        from pypy.translator.transform import insert_ll_stackcheck
        def g(x):
            return f(x)

        def f(x):
            if x:
                return g(x - 1)
            return 1
        t, wa = self.translate(f, [int])
        insert_ll_stackcheck(t)
        ggraph = graphof(t, g)
        result = wa.analyze(ggraph.startblock.operations[-1])
        assert not result

    def test_method(self):
        class A(object):
            def f(self):
                self.x = 1
                return 1
            def m(self):
                raise ValueError
        class B(A):
            def f(self):
                return 2
            def m(self):
                return 3
        def f(a):
            return a.f()
        def m(a):
            return a.m()
        def h(flag):
            if flag:
                obj = A()
            else:
                obj = B()
            f(obj)
            m(obj)
        
        t, wa = self.translate(h, [int])
        hgraph = graphof(t, h)
        # fiiiish :-(
        block = hgraph.startblock.exits[0].target.exits[0].target
        op_call_f = block.operations[0]
        op_call_m = block.operations[1]

        # check that we fished the expected ops
        def check_call(op, fname):
            assert op.opname == "direct_call"
            assert get_funcobj(op.args[0].value)._name == fname
        check_call(op_call_f, "f")
        check_call(op_call_m, "m")

        result = wa.analyze(op_call_f)
        assert len(result) == 1
        (struct, T, name), = result
        assert struct == "struct"
        assert name.endswith("x")
        assert not wa.analyze(op_call_m)

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
        t, wa = self.translate(f, [int])
        fgraph = graphof(t, f)
        result = wa.analyze(fgraph.startblock.operations[0])
        assert result is top_set

    def test_llexternal(self):
        from pypy.rpython.lltypesystem.rffi import llexternal
        from pypy.rpython.lltypesystem import lltype
        z = llexternal('z', [lltype.Signed], lltype.Signed)
        def f(x):
            return z(x)
        t, wa = self.translate(f, [int])
        fgraph = graphof(t, f)
        backend_optimizations(t)
        assert fgraph.startblock.operations[0].opname == 'direct_call'

        result = wa.analyze(fgraph.startblock.operations[0])
        assert not result

    def test_list(self):
        def g(x, y, z):
            return f(x, y, z)
        def f(x, y, z):
            l = [0] * x
            l.append(y)
            return len(l) + z


        t, wa = self.translate(g, [int, int, int])
        ggraph = graphof(t, g)
        assert ggraph.startblock.operations[0].opname == 'direct_call'

        result = sorted(wa.analyze(ggraph.startblock.operations[0]))
        array, A = result[0]
        assert array == "array"
        assert A.TO.OF == lltype.Signed

        struct, S1, name = result[1]
        assert struct == "struct"
        assert S1.TO.items == A
        assert S1.TO.length == lltype.Signed
        assert name == "items"

        struct, S2, name = result[2]
        assert struct == "struct"
        assert name == "length"
        assert S1 is S2
