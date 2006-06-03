from pypy.translator.translator import TranslationContext
from pypy.rpython.test import snippet
from pypy.rpython.test.test_llinterp import interpret
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin

class TestSnippet(object):

    def _test(self, func, types):
        t = TranslationContext()
        t.buildannotator().build_types(func, types)
        t.buildrtyper().specialize()
        t.checkgraphs()    
 
    def test_not1(self):
        self._test(snippet.not1, [float])

    def test_not2(self):
        self._test(snippet.not2, [float])

    def test_float1(self):
        self._test(snippet.float1, [float])

    def test_float_cast1(self):
        self._test(snippet.float_cast1, [float])

    def DONTtest_unary_operations(self):
        # XXX TODO test if all unary operations are implemented
        for opname in annmodel.UNARY_OPERATIONS:
            print 'UNARY_OPERATIONS:', opname

    def DONTtest_binary_operations(self):
        # XXX TODO test if all binary operations are implemented
        for opname in annmodel.BINARY_OPERATIONS:
            print 'BINARY_OPERATIONS:', opname

def test_int_conversion():
    def fn(f):
        return int(f)

    res = interpret(fn, [1.0])
    assert res == 1
    assert type(res) is int 
    res = interpret(fn, [2.34])
    assert res == fn(2.34) 

def test_hash():
    def fn(f):
        return hash(f)
    res = interpret(fn, [1.5])
    assert res == hash(1.5)

class BaseTestRfloat(BaseRtypingTest):
    
    def test_float2str(self):
        def fn(f):
            return str(f)

        res = self.interpret(fn, [1.5])
        assert float(self.ll_to_string(res)) == 1.5

    def test_string_mod_float(self):
        def fn(f):
            return '%f' % f

        res = self.interpret(fn, [1.5])
        assert float(self.ll_to_string(res)) == 1.5

class TestLLtype(BaseTestRfloat, LLRtypeMixin):
    pass

class TestOOtype(BaseTestRfloat, OORtypeMixin):
    pass
