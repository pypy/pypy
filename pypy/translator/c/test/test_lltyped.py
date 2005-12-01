from pypy.rpython.lltypesystem.lltype import *
from pypy.translator.c.test import test_typed


class TestLowLevelType:
    getcompiled = test_typed.TestTypedTestCase().getcompiled

    def test_simple(self):
        S = GcStruct("s", ('v', Signed))
        def llf():
            s = malloc(S)
            return s.v
        fn = self.getcompiled(llf)
        assert fn() == 0

    def test_simple2(self):
        S = Struct("s", ('v', Signed))
        S2 = GcStruct("s2", ('a',S), ('b',S))
        def llf():
            s = malloc(S2)
            s.a.v = 6
            s.b.v = 12
            return s.a.v + s.b.v
        fn = self.getcompiled(llf)
        assert fn() == 18
