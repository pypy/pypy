import py
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.simplify import get_funcobj
from pypy.translator.backendopt.writeanalyze import WriteAnalyzer, top_set
from pypy.translator.backendopt.writeanalyze import ReadWriteAnalyzer
from pypy.translator.backendopt.all import backend_optimizations
from pypy.conftest import option


class BaseTest(object):

    type_system = None
    Analyzer = WriteAnalyzer
    
    def translate(self, func, sig):
        t = TranslationContext()
        t.buildannotator().build_types(func, sig)
        t.buildrtyper(type_system=self.type_system).specialize()
        if option.view:
            t.view()
        return t, self.Analyzer(t)


class BaseTestWriteAnalyze(BaseTest):

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

    def test_write_to_new_struct(self):
        class A(object):
            pass
        def f(x):
            a = A()
            a.baz = x   # writes to a fresh new struct are ignored
            return a
        t, wa = self.translate(f, [int])
        fgraph = graphof(t, f)
        result = wa.analyze_direct_call(fgraph)
        assert not result

    def test_write_to_new_struct_2(self):
        class A(object):
            pass
        def f(x):
            a = A()
            # a few extra blocks
            i = 10
            while i > 0:
                i -= 1
            # done
            a.baz = x   # writes to a fresh new struct are ignored
            return a
        t, wa = self.translate(f, [int])
        fgraph = graphof(t, f)
        result = wa.analyze_direct_call(fgraph)
        assert not result

    def test_write_to_new_struct_3(self):
        class A(object):
            pass
        prebuilt = A()
        def f(x):
            if x > 5:
                a = A()
            else:
                a = A()
            a.baz = x
            return a
        t, wa = self.translate(f, [int])
        fgraph = graphof(t, f)
        result = wa.analyze_direct_call(fgraph)
        assert not result

    def test_write_to_new_struct_4(self):
        class A(object):
            pass
        prebuilt = A()
        def f(x):
            if x > 5:
                a = A()
            else:
                a = prebuilt
            a.baz = x
            return a
        t, wa = self.translate(f, [int])
        fgraph = graphof(t, f)
        result = wa.analyze_direct_call(fgraph)
        assert len(result) == 1 and 'baz' in list(result)[0][-1]

    def test_write_to_new_struct_5(self):
        class A(object):
            baz = 123
        def f(x):
            if x:
                a = A()
            else:
                a = A()
            a.baz += 1
        t, wa = self.translate(f, [int])
        fgraph = graphof(t, f)
        result = wa.analyze_direct_call(fgraph)
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
        if self.type_system == 'lltype':
            assert result is top_set
        else:
            assert not result # ootype is more precise in this case

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

    def test_contains(self):
        def g(x, y, z):
            l = [x]
            return f(l, y, z)
        def f(x, y, z):
            return y in x


        t, wa = self.translate(g, [int, int, int])
        ggraph = graphof(t, g)
        assert ggraph.startblock.operations[-1].opname == 'direct_call'

        result = wa.analyze(ggraph.startblock.operations[-1])
        assert not result


class TestLLtype(BaseTestWriteAnalyze):
    type_system = 'lltype'

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

    def test_llexternal_with_callback(self):
        from pypy.rpython.lltypesystem.rffi import llexternal
        from pypy.rpython.lltypesystem import lltype

        class Abc:
            pass
        abc = Abc()

        FUNC = lltype.FuncType([lltype.Signed], lltype.Signed)
        z = llexternal('z', [lltype.Ptr(FUNC)], lltype.Signed)
        def g(n):
            abc.foobar = n
            return n + 1
        def f(x):
            return z(g)
        t, wa = self.translate(f, [int])
        fgraph = graphof(t, f)
        backend_optimizations(t)
        assert fgraph.startblock.operations[0].opname == 'direct_call'

        result = wa.analyze(fgraph.startblock.operations[0])
        assert len(result) == 1
        (struct, T, name), = result
        assert struct == "struct"
        assert name.endswith("foobar")


class TestOOtype(BaseTestWriteAnalyze):
    type_system = 'ootype'
    
    def test_array(self):
        def g(x, y, z):
            return f(x, y, z)
        def f(x, y, z):
            l = [0] * x
            l[1] = 42
            return len(l) + z

        t, wa = self.translate(g, [int, int, int])
        ggraph = graphof(t, g)
        assert ggraph.startblock.operations[0].opname == 'direct_call'

        result = sorted(wa.analyze(ggraph.startblock.operations[0]))
        assert len(result) == 1
        array, A = result[0]
        assert array == 'array'
        assert A.ITEM is ootype.Signed
        
    def test_list(self):
        def g(x, y, z):
            return f(x, y, z)
        def f(x, y, z):
            l = [0] * x
            l.append(z)
            return len(l) + z

        t, wa = self.translate(g, [int, int, int])
        ggraph = graphof(t, g)
        assert ggraph.startblock.operations[0].opname == 'direct_call'

        result = wa.analyze(ggraph.startblock.operations[0])
        assert result is top_set


class TestLLtypeReadWriteAnalyze(BaseTest):
    Analyzer = ReadWriteAnalyzer
    type_system = 'lltype'

    def test_read_simple(self):
        def g(x):
            return True

        def f(x):
            return g(x - 1)
        t, wa = self.translate(f, [int])
        fgraph = graphof(t, f)
        result = wa.analyze(fgraph.startblock.operations[0])
        assert not result

    def test_read_really(self):
        class A(object):
            def __init__(self, y):
                self.y = y
            def f(self):
                self.x = 1
                return self.y
        def h(flag):
            obj = A(flag)
            return obj.f()
        
        t, wa = self.translate(h, [int])
        hgraph = graphof(t, h)
        op_call_f = hgraph.startblock.operations[-1]

        # check that we fished the expected ops
        assert op_call_f.opname == "direct_call"
        assert get_funcobj(op_call_f.args[0].value)._name == 'A.f'

        result = wa.analyze(op_call_f)
        assert len(result) == 2
        result = list(result)
        result.sort()
        [(struct1, T1, name1), (struct2, T2, name2)] = result
        assert struct1 == "readstruct"
        assert name1.endswith("y")
        assert struct2 == "struct"
        assert name2.endswith("x")
        assert T1 == T2

    def test_contains(self):
        def g(x, y, z):
            l = [x]
            return f(l, y, z)
        def f(x, y, z):
            return y in x

        t, wa = self.translate(g, [int, int, int])
        ggraph = graphof(t, g)
        assert ggraph.startblock.operations[-1].opname == 'direct_call'

        result = wa.analyze(ggraph.startblock.operations[-1])
        ARRAYPTR = list(result)[0][1]
        assert list(result) == [("readarray", ARRAYPTR)]
        assert isinstance(ARRAYPTR.TO, lltype.GcArray)

    def test_adt_method(self):
        def ll_callme(n):
            return n
        ll_callme = lltype.staticAdtMethod(ll_callme)
        S = lltype.GcStruct('S', ('x', lltype.Signed),
                            adtmeths = {'yep': True,
                                        'callme': ll_callme})
        def g(p, x, y, z):
            p.x = x
            if p.yep:
                z *= p.callme(y)
            return z
        def f(x, y, z):
            p = lltype.malloc(S)
            return g(p, x, y, z)

        t, wa = self.translate(f, [int, int, int])
        fgraph = graphof(t, f)
        assert fgraph.startblock.operations[-1].opname == 'direct_call'

        result = wa.analyze(fgraph.startblock.operations[-1])
        assert list(result) == [("struct", lltype.Ptr(S), "x")]
