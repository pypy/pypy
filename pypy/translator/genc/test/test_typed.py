import autopath
import sys
from pypy.translator.genc.ctyper import GenCSpecializer
from pypy.translator.translator import Translator
from pypy.translator.test import snippet 
from pypy.translator.tool.buildpyxmodule import skip_missing_compiler

from pypy.translator.genc.test.test_annotated import TestAnnotatedTestCase as _TestAnnotatedTestCase


class TestTypedTestCase:##!!(_TestAnnotatedTestCase):

    def getcompiled(self, func):
        t = Translator(func, simplifying=True)
        # builds starting-types from func_defs 
        argstypelist = []
        if func.func_defaults:
            for spec in func.func_defaults:
                if isinstance(spec, tuple):
                    spec = spec[0] # use the first type only for the tests
                argstypelist.append(spec)
        t.view()##!!
        a = t.annotate(argstypelist)
        t.view()##!!
        a.simplify()
        t.view()##!!
        GenCSpecializer(a).specialize()
        t.view()##!!
        t.checkgraphs()
        return skip_missing_compiler(t.ccompile)

    def xxx_testint_overflow(self):
        fn = self.getcompiled(snippet.add_func)
        raises(OverflowError, fn, sys.maxint)

    def xxx_testint_div_ovf_zer(self):
        fn = self.getcompiled(snippet.div_func)
        raises(OverflowError, fn, -1)
        raises(ZeroDivisionError, fn, 0)

    def testint_mod_ovf_zer(self):
        fn = self.getcompiled(snippet.mod_func)
        raises(OverflowError, fn, -1)
        raises(ZeroDivisionError, fn, 0)

    def xxx_testint_rshift_val(self):
        fn = self.getcompiled(snippet.rshift_func)
        raises(ValueError, fn, -1)

    def testint_lshift_ovf_val(self):
        fn = self.getcompiled(snippet.lshift_func)
        raises(ValueError, fn, -1)
        raises(OverflowError, fn, 1)
        