import autopath
import sys
from pypy.translator.genc.ctyper import GenCSpecializer
from pypy.translator.translator import Translator
from pypy.translator.test import snippet 
from pypy.translator.tool.buildpyxmodule import skip_missing_compiler

from pypy.translator.genc.test.test_annotated import TestAnnotatedTestCase as _TestAnnotatedTestCase


class TestTypedTestCase(_TestAnnotatedTestCase):

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
        GenCSpecializer(a).specialize()
        t.checkgraphs()
        return skip_missing_compiler(t.ccompile)

    def test_int_overflow(self):
        fn = self.getcompiled(snippet.simple_func)
        raises(OverflowError, fn, sys.maxint+1)
