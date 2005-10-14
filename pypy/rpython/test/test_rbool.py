from pypy.translator.translator import Translator
from pypy.rpython.lltype import pyobjectptr
from pypy.rpython.rtyper import RPythonTyper
from pypy.annotation import model as annmodel
from pypy.rpython.test import snippet
from pypy.rpython.test.test_llinterp import interpret


class TestSnippet(object):
    
    def _test(self, func, types):
        t = Translator(func)
        t.annotate(types)
        typer = RPythonTyper(t.annotator)
        typer.specialize()
        t.checkgraphs()  
        #if func == snippet.bool_cast1:
        #    t.view()

    def test_not1(self):
        self._test(snippet.not1, [bool])

    def test_not2(self):
        self._test(snippet.not2, [bool])

    def test_bool1(self):
        self._test(snippet.bool1, [bool])

    def test_bool_cast1(self):
        self._test(snippet.bool_cast1, [bool])

    def DONTtest_unary_operations(self):
        # XXX TODO test if all unary operations are implemented
        for opname in annmodel.UNARY_OPERATIONS:
            print 'UNARY_OPERATIONS:', opname

    def DONTtest_binary_operations(self):
        # XXX TODO test if all binary operations are implemented
        for opname in annmodel.BINARY_OPERATIONS:
            print 'BINARY_OPERATIONS:', opname

    def test_bool2int(self):
        def f(n):
            if n:
                n = 2
            return n
        res = interpret(f, [False])
        assert res == 0 and res is not False   # forced to int by static typing
        res = interpret(f, [True])
        assert res == 2
