from pypy.rpython.lltype import *
from pypy.annotation import model as annmodel
from pypy.rpython.annlowlevel import annotate_lowlevel_helper

# helpers

def annotated_calls(ann, ops=('simple_call,')):
    for block in ann.annotated:
        for op in block.operations:
            if op.opname in ops:
                yield op

def derived(op, orig):
    if op.args[0].value.__name__.startswith(orig):
        return op.args[0].value
    else:
        return None

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

    def test_cast_pointer(self):
        S3 = GcStruct("s3", ('a', Signed))
        S2 = GcStruct("s3", ('sub', S3))
        S1 = GcStruct("s1", ('sub', S2))
        PS1 = Ptr(S1)
        PS2 = Ptr(S2)
        PS3 = Ptr(S3)
        def llwitness(p12, p13, p21, p23, p31, p32):
            pass
        def llf():
            p1 = malloc(S1)
            p2 = p1.sub
            p3 = p2.sub
            p12 = cast_pointer(PS1, p2)
            p13 = cast_pointer(PS1, p3)
            p21 = cast_pointer(PS2, p1)
            p23 = cast_pointer(PS2, p3)
            p31 = cast_pointer(PS3, p1)
            p32 = cast_pointer(PS3, p2)
            llwitness(p12, p13, p21, p23, p31, p32)
        a = self.RPythonAnnotator()
        s, dontcare = annotate_lowlevel_helper(a, llf, [])
        
        spec_llwitness = None
        for call in annotated_calls(a):
            spec_llwitness = derived(call, 'llwitness')

        g = a.translator.flowgraphs[spec_llwitness]
        bindings = [a.binding(v) for v in g.getargs()]
        assert [x.ll_ptrtype for x in bindings] == [PS1, PS1, PS2, PS2, PS3, PS3]
            

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
        for call in annotated_calls(a):
            if derived(call, "ll_"):
                    for_[tuple([x.value for x in call.args[0:2]])] = True
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
 
    def test_ll_calling_ll2(self):
        A = GcArray(Float)
        B = GcArray(Signed)
        def ll_make(T, n):
            x = malloc(T, n)
            return x
        def ll_get(x, i):
            return x[i]
        def makelen4(T):
            return ll_make(T, 4)
        def llf():
            a = ll_make(A, 3)
            b = ll_make(B, 2)
            a[0] = 1.0
            b[1] = 3
            y0 = ll_get(a, 1)
            y1 = ll_get(b, 1)
            #
            a2 = makelen4(A)
            a2[0] = 2.0
            return ll_get(a2, 1)
        a = self.RPythonAnnotator()
        s, llf2 = annotate_lowlevel_helper(a, llf, [])
        assert llf2 is llf
        assert s == annmodel.SomeFloat()
        g = a.translator.getflowgraph(llf)
        for_ = {}
        def q(v):
            s = a.binding(v)
            if s.is_constant():
                return s.const
            else:
                return s.ll_ptrtype

        for call in annotated_calls(a):
            if derived(call, "ll_") or derived(call, "makelen4"):
                for_[tuple([q(x) for x in call.args[0:2]])] = True
                
        assert len(for_) == 5
        vTs = []
        for func, T in for_.keys():
            g = a.translator.getflowgraph(func)
            args = g.getargs()
            rv = g.getreturnvar()
            if isinstance(T, ContainerType):
                if len(args) == 2:
                    vT, vn = args
                    vTs.append(vT)
                    assert a.binding(vT) == annmodel.SomePBC({T: True})
                    assert a.binding(vn).knowntype == int
                    assert a.binding(rv).ll_ptrtype.TO == T
                else:
                    vT, = args
                    vTs.append(vT)
                    assert a.binding(vT) == annmodel.SomePBC({T: True})
                    assert a.binding(rv).ll_ptrtype.TO == T
            else:
                vp, vi = args
                assert a.binding(vi).knowntype == int
                assert a.binding(vp).ll_ptrtype == T
                assert a.binding(rv) == annmodel.lltype_to_annotation(T.TO.OF)
        return a, vTs
