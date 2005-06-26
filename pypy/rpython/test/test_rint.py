from pypy.translator.translator import Translator
from pypy.rpython.rtyper import RPythonTyper
from pypy.annotation import model as annmodel
from pypy.rpython.test import snippet
from pypy.rpython.test.test_llinterp import interpret
from pypy.rpython.rarithmetic import r_uint


class TestSnippet(object):
    
    def _test(self, func, types):
        t = Translator(func)
        t.annotate(types)
        typer = RPythonTyper(t.annotator)
        typer.specialize()
        t.checkgraphs() 
        #if func == snippet.int_cast1:
        #    t.view()
    
    def test_not1(self):
        self._test(snippet.not1, [int])

    def test_not2(self):
        self._test(snippet.not2, [int])

    def test_int1(self):
        self._test(snippet.int1, [int])

    def test_int_cast1(self):
        self._test(snippet.int_cast1, [int])

    def DONTtest_unary_operations(self):
        # XXX TODO test if all unary operations are implemented
        for opname in annmodel.UNARY_OPERATIONS:
            print 'UNARY_OPERATIONS:', opname

    def DONTtest_binary_operations(self):
        # XXX TODO test if all binary operations are implemented
        for opname in annmodel.BINARY_OPERATIONS:
            print 'BINARY_OPERATIONS:', opname


def test_char_constant():
    def dummyfn(i):
        return chr(i)
    res = interpret(dummyfn, [ord(' ')])
    assert res == ' '
    res = interpret(dummyfn, [0])
    assert res == '\0'
    res = interpret(dummyfn, [ord('a')])
    assert res == 'a'
    
def test_str_of_int():
    def dummy(i):
        return str(i)
    
    res = interpret(dummy, [0])
    assert ''.join(res.chars) == '0'

    res = interpret(dummy, [1034])
    assert ''.join(res.chars) == '1034'

    res = interpret(dummy, [-123])
    assert ''.join(res.chars) == '-123'
    
def test_hex_of_int():
    def dummy(i):
        return hex(i)
    
    res = interpret(dummy, [0])
    assert ''.join(res.chars) == '0x0'

    res = interpret(dummy, [1034])
    assert ''.join(res.chars) == '0x40a'

    res = interpret(dummy, [-123])
    assert ''.join(res.chars) == '-0x7b'
    
def test_unsigned():
    def dummy(i):
        i = r_uint(i)
        j = r_uint(12)
        return i < j

    res = interpret(dummy,[0])
    assert res is True

    res = interpret(dummy, [-1])
    assert res is False    # -1 ==> 0xffffffff

