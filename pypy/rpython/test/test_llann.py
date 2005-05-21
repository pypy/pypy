from pypy.rpython.lltypes import *
from pypy.annotation import model as annmodel


class TestLowLevelAnnotateTestCase:
    objspacename = 'flow'

    from pypy.translator.annrpython import RPythonAnnotator

    def test_simple(self):
        S = GcStruct("s", ('v', Signed))
        def llf():
            s = malloc(S)
            return s.v
        a = self.RPythonAnnotator()
        s = a.build_types(llf, [])
        assert s.knowntype == int

    def test_simple2(self):
        S = Struct("s", ('v', Signed))
        S2 = GcStruct("s2", ('a',S), ('b',S))
        def llf():
            s = malloc(S2)
            return s.a.v+s.b.v
        a = self.RPythonAnnotator()
        s = a.build_types(llf, [])
        assert s.knowntype == int

    def test_array(self):
        A = GcArray(('v', Signed))
        def llf():
            a = malloc(A, 1)
            return a[0].v
        a = self.RPythonAnnotator()
        s = a.build_types(llf, [])
        assert s.knowntype == int

    def test_cast_flags(self):
        S1 = GcStruct("s1", ('a', Signed), ('b', Unsigned))
        NGCPS1 = NonGcPtr(S1)
        def llf():
            p1 = malloc(S1)
            p2 = cast_flags(NGCPS1, p1)
            return p2
        a = self.RPythonAnnotator()
        s = a.build_types(llf, [])
        assert isinstance(s, annmodel.SomePtr)
        assert s.ll_ptrtype == NGCPS1
        
    def test_cast_parent(self):
        S2 = Struct("s2", ('a', Signed))
        S1 = GcStruct("s1", ('sub1', S2), ('sub2', S2))
        GCPS1 = GcPtr(S1)
        NGCPS1 = NonGcPtr(S1)
        NGCPS2 = NonGcPtr(S2)
        def llf():
            p1 = malloc(S1)
            p2 = p1.sub1
            p3 = cast_flags(NGCPS2, p2)
            p4 = cast_parent(NGCPS1, p3)
            p5 = cast_flags(GCPS1, p4)
            return p5
        a = self.RPythonAnnotator()
        s = a.build_types(llf, [])
        assert isinstance(s, annmodel.SomePtr)
        assert s.ll_ptrtype == GCPS1

    def test_cast_parent_from_gc(self):
        S2 = GcStruct("s2", ('a', Signed))
        S1 = GcStruct("s1", ('sub1', S2), ('x', Signed))
        GCPS1 = GcPtr(S1)
        def llf():
            p1 = malloc(S1)
            p2 = p1.sub1
            p3 = cast_parent(GCPS1, p2)
            return p3
        a = self.RPythonAnnotator()
        s = a.build_types(llf, [])
        assert isinstance(s, annmodel.SomePtr)
        assert s.ll_ptrtype == GCPS1

    def test_array_length(self):
        A = GcArray(('v', Signed))
        def llf():
            a = malloc(A, 1)
            return len(a)
        a = self.RPythonAnnotator()
        s = a.build_types(llf, [])
        assert s.knowntype == int

    def test_funcptr(self):
        F = FuncType((Signed,), Signed)
        PF = NonGcPtr(F)
        def llf(p):
            return p(0)
        a = self.RPythonAnnotator()
        s = a.build_types(llf, [PF])
        assert s.knowntype == int
 
