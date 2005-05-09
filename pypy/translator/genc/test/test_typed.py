import autopath
import sys
import py.test
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
        fn = self.getcompiled(snippet.add_func)
        raises(OverflowError, fn, sys.maxint)

    def test_int_div_ovf_zer(self): # 
        py.test.skip("right now aborting python wiht Floating Point Error!")
        fn = self.getcompiled(snippet.div_func)
        raises(OverflowError, fn, -1)
        raises(ZeroDivisionError, fn, 0)

    def test_int_mod_ovf_zer(self):
        py.test.skip("right now aborting python wiht Floating Point Error!")        
        fn = self.getcompiled(snippet.mod_func)
        raises(OverflowError, fn, -1)
        raises(ZeroDivisionError, fn, 0)

    def test_int_rshift_val(self):
        fn = self.getcompiled(snippet.rshift_func)
        raises(ValueError, fn, -1)

    def test_int_lshift_ovf_val(self):
        fn = self.getcompiled(snippet.lshift_func)
        raises(ValueError, fn, -1)
        raises(OverflowError, fn, 1)
        
