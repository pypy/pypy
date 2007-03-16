import sys
from pypy.translator.translator import TranslationContext
from pypy.rpython.test import snippet
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin
from pypy.rlib.rarithmetic import r_uint, r_longlong

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

    def test_int_conversion(self):
        def fn(f):
            return int(f)

        res = self.interpret(fn, [1.0])
        assert res == 1
        assert type(res) is int 
        res = self.interpret(fn, [2.34])
        assert res == fn(2.34) 

    def test_longlong_conversion(self):
        def fn(f):
            return r_longlong(f)

        res = self.interpret(fn, [1.0])
        assert res == 1
        assert self.is_of_type(res, r_longlong)
        res = self.interpret(fn, [2.34])
        assert res == fn(2.34) 
        big = float(0x7fffffffffffffff)
        x = big - 1.e10
        assert x != big
        y = fn(x)
        assert fn(x) == 9223372026854775808

    def test_to_r_uint(self):
        def fn(x):
            return r_uint(x)

        res = self.interpret(fn, [12.34])
        assert res == 12
        bigval = sys.maxint * 1.234
        res = self.interpret(fn, [bigval])
        assert long(res) == long(bigval)

    def test_from_r_uint(self):
        def fn(n):
            return float(r_uint(n)) / 2

        res = self.interpret(fn, [41])
        assert res == 20.5
        res = self.interpret(fn, [-9])
        assert res == 0.5 * ((sys.maxint+1)*2 - 9)

    def test_float_constant_conversions(self):
        DIV = r_longlong(10 ** 10)
        def fn():
            return 420000000000.0 / DIV

        res = self.interpret(fn, [])
        assert res == 42.0

class TestLLtype(BaseTestRfloat, LLRtypeMixin):

    def test_hash(self):
        def fn(f):
            return hash(f)
        res = self.interpret(fn, [1.5])
        assert res == hash(1.5)


class TestOOtype(BaseTestRfloat, OORtypeMixin):
    pass
