from pypy.rpython.lltypes import *


class TestLowLevelAnnotateTestCase:
    objspacename = 'flow'

    from pypy.translator.annrpython import RPythonAnnotator

    def test_simple(self):
        S = Struct("s", ('v', Signed))
        def llf():
            s = malloc(S)
            return s.v
        a = self.RPythonAnnotator()
        s = a.build_types(llf, [])
        assert s.knowntype == int

    def test_simple2(self):
        S = Struct("s", ('v', Signed))
        S2 = Struct("s2", ('a',S), ('b',S))
        def llf():
            s = malloc(S2)
            return s.a.v+s.b.v
        a = self.RPythonAnnotator()
        s = a.build_types(llf, [])
        assert s.knowntype == int
