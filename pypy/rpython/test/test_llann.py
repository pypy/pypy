from pypy.rpython.lltype import *
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
        s = a.build_types(llf, [annmodel.SomePtr(PS1)])
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
        s = a.build_types(llf, [])
        assert isinstance(s, annmodel.SomePtr)
        assert s.ll_ptrtype == PS1

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
        PF = Ptr(F)
        def llf(p):
            return p(0)
        a = self.RPythonAnnotator()
        s = a.build_types(llf, [annmodel.SomePtr(PF)])
        assert s.knowntype == int
 
