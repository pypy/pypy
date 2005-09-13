import autopath
from pypy.translator.tool.cbuild import skip_missing_compiler
from pypy.translator.translator import Translator

from pypy.translator.c.test.test_typed import TestTypedTestCase as _TestTypedTestCase


class TestTypedOptimizedTestCase(_TestTypedTestCase):

    def getcompiled(self, func):
        t = Translator(func, simplifying=True)
        # builds starting-types from func_defs 
        argstypelist = []
        if func.func_defaults:
            for spec in func.func_defaults:
                if isinstance(spec, tuple):
                    spec = spec[0] # use the first type only for the tests
                argstypelist.append(spec)
        a = t.annotate(argstypelist)
        a.simplify()
        t.specialize()
        t.backend_optimizations()
        t.checkgraphs()
        return skip_missing_compiler(t.ccompile)

    def test_remove_same_as(self):
        def f(n=bool):
            if bool(bool(bool(n))):
                return 123
            else:
                return 456
        fn = self.getcompiled(f)
        assert f(True) == 123
        assert f(False) == 456
