from pypy.rpython.lltype import *
from pypy.translator.tool.buildpyxmodule import skip_missing_compiler
from pypy.translator.translator import Translator


class TestLowLevelType:
    objspacename = 'flow'

    def getcompiled(self, func, argstypelist=[]):
        t = Translator(func, simplifying=True)
        # builds starting-types from func_defs 
        a = t.annotate(argstypelist)
        a.simplify()
        t.specialize()
        t.checkgraphs()
        #t.view()
        return skip_missing_compiler(t.ccompile)

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
            return s.a.v+s.b.v
        fn = self.getcompiled(llf)
        assert fn() == 18
