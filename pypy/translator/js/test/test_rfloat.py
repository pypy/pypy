
import py
from pypy.translator.js.test.runtest import JsTest
from pypy.rpython.test.test_rfloat import BaseTestRfloat
from pypy.rlib.rarithmetic import r_uint, r_longlong

class TestJsFloat(JsTest, BaseTestRfloat):
    def test_from_r_uint(self):
        py.test.skip("Not implemented")

    def test_longlong_conversion(self):
        def fn(f):
            return r_longlong(f)

        res = self.interpret(fn, [1.0])
        assert res == 1
        #assert self.is_of_type(res, r_longlong)
        res = self.interpret(fn, [2.34])
        assert res == fn(2.34) 
        big = float(0x7fffffffffffffff)
        x = big - 1.e10
        assert x != big
        y = fn(x)
        assert fn(x) == 9223372026854775808

    def test_float2str(self):
        def fn(f):
            return str(f)

        res = self.interpret(fn, [1.5])
        assert float(self.ll_to_string(res)) == 1.5
        res = self.interpret(fn, [-1.5])
        assert float(self.ll_to_string(res)) == -1.5
        py.test.skip("Partly works, needs adapting testing infrastructure")
        inf = 1e200 * 1e200
        nan = inf/inf
        res = self.interpret(fn, [inf])
        assert self.ll_to_string(res) == self.inf
        res = self.interpret(fn, [-inf])
        assert self.ll_to_string(res) == self.minus_inf
        res = self.interpret(fn, [nan])
        assert self.ll_to_string(res) == self.nan


    def test_r_singlefloat(self):
        py.test.skip("not implemented: single-precision floats")
