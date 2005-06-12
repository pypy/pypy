from pypy.rpython.lltype import *
from pypy.annotation import model as annmodel
from pypy.rpython.annlowlevel import annotate_lowlevel_helper

class TestLowLevelAnnotateTestCase:
    objspacename = 'flow'

    from pypy.translator.annrpython import RPythonAnnotator

    def test_simple(self):
        S = GcStruct("s", ('v', Signed))
        def llf():
            s = malloc(S)
            return s.v
        a = self.RPythonAnnotator()
        s, dontcare = annotate_lowlevel_helper(a, llf, [])
        assert s.knowntype == int

    def test_simple2(self):
        S = Struct("s", ('v', Signed))
        S2 = GcStruct("s2", ('a',S), ('b',S))
        def llf():
            s = malloc(S2)
            return s.a.v+s.b.v
        a = self.RPythonAnnotator()
        s, dontcare = annotate_lowlevel_helper(a, llf, [])
        assert s.knowntype == int

    def test_array(self):
        A = GcArray(('v', Signed))
        def llf():
            a = malloc(A, 1)
            return a[0].v
        a = self.RPythonAnnotator()
        s, dontcare = annotate_lowlevel_helper(a, llf, [])
        assert s.knowntype == int

    def test_prim_array(self):
        A = GcArray(Signed)
        def llf():
            a = malloc(A, 1)
            return a[0]
        a = self.RPythonAnnotator()
        s, dontcare = annotate_lowlevel_helper(a, llf, [])
        assert s.knowntype == int

    def test_prim_array_setitem(self):
        A = GcArray(Signed)
        def llf():
            a = malloc(A, 1)
            a[0] = 3
            return a[0]
        a = self.RPythonAnnotator()
        s, dontcare = annotate_lowlevel_helper(a, llf, [])
        assert s.knowntype == int        
        
    def test_cast_parent(self):
        S2 = Struct("s2", ('a', Signed))
        S1 = Struct("s1", ('sub1', S2), ('sub2', S2))
        PS1 = Ptr(S1)
        PS2 = Ptr(S2)
        def llf(p1):
            p2 = p1.sub1
            p3 = cast_parent(PS1, p2)
            return p3
        a = self.RPythonAnnotator()
        s, dontcare = annotate_lowlevel_helper(a, llf, [annmodel.SomePtr(PS1)])
        assert isinstance(s, annmodel.SomePtr)
        assert s.ll_ptrtype == PS1

    def test_cast_parent_from_gc(self):
        S2 = GcStruct("s2", ('a', Signed))
        S1 = GcStruct("s1", ('sub1', S2), ('x', Signed))
        PS1 = Ptr(S1)
        def llf():
            p1 = malloc(S1)
            p2 = p1.sub1
            p3 = cast_parent(PS1, p2)
            return p3
        a = self.RPythonAnnotator()
        s, dontcare = annotate_lowlevel_helper(a, llf, [])
        assert isinstance(s, annmodel.SomePtr)
        assert s.ll_ptrtype == PS1

    def test_array_length(self):
        A = GcArray(('v', Signed))
        def llf():
            a = malloc(A, 1)
            return len(a)
        a = self.RPythonAnnotator()
        s, dontcare = annotate_lowlevel_helper(a, llf, [])
        assert s.knowntype == int

    def test_funcptr(self):
        F = FuncType((Signed,), Signed)
        PF = Ptr(F)
        def llf(p):
            return p(0)
        a = self.RPythonAnnotator()
        s, dontcare = annotate_lowlevel_helper(a, llf, [annmodel.SomePtr(PF)])
        assert s.knowntype == int
 

    def test_ll_calling_ll(self):
        A = GcArray(Float)
        B = GcArray(Signed)
        def ll_make(T, n):
            x = malloc(T, n)
            return x
        def ll_get(T, x, i):
            return x[i]
        def llf():
            a = ll_make(A, 3)
            b = ll_make(B, 2)
            a[0] = 1.0
            b[1] = 3
            y0 = ll_get(A, a, 1)
            y1 = ll_get(B, b, 1)
            #
            a2 = ll_make(A, 4)
            a2[0] = 2.0
            return ll_get(A, a2, 1)
        a = self.RPythonAnnotator()
        s, llf2 = annotate_lowlevel_helper(a, llf, [])
        assert llf2 is llf
        assert s == annmodel.SomeFloat()
        g = a.translator.getflowgraph(llf)
        for_ = {}
        for block in a.annotated:
            for op in block.operations:
                if op.opname == 'simple_call' and op.args[0].value.__name__.startswith("ll_"):
                    for_[tuple([x.value for x in op.args[0:2]])] = True
        assert len(for_) == 4
        vTs = []
        for func, T in for_.keys():
            g = a.translator.getflowgraph(func)
            args = g.getargs()
            rv = g.getreturnvar()
            if len(args) == 2:
                vT, vn = args
                vTs.append(vT)
                assert a.binding(vT) == annmodel.SomePBC({T: True})
                assert a.binding(vn).knowntype == int
                assert a.binding(rv).ll_ptrtype.TO == T
            else:
                vT, vp, vi = args
                vTs.append(vT)
                assert a.binding(vT) == annmodel.SomePBC({T: True})
                assert a.binding(vi).knowntype == int
                assert a.binding(vp).ll_ptrtype.TO == T
                assert a.binding(rv) == annmodel.lltype_to_annotation(T.OF)
        return a, vTs
 
 
