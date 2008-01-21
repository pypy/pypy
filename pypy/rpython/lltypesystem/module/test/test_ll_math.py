
""" Just another bunch of tests for llmath, run on top of llinterp
"""

from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin
from pypy.rpython.lltypesystem.module import ll_math
import math

# XXX no OORtypeMixin here

class TestMath(BaseRtypingTest, LLRtypeMixin):
    def new_unary_test(name):
        def next_test(self):
            def f(x):
                return getattr(math, name)(x)
            assert self.interpret(f, [0.3]) == f(0.3)
        return next_test

    def new_binary_test(name):
        def next_test(self):
            def f(x, y):
                return getattr(math, name)(x, y)
            assert self.interpret(f, [0.3, 0.4]) == f(0.3, 0.4)
        return next_test
    
    for name in ll_math.unary_math_functions:
        func_name = 'test_%s' % (name,)
        next_test = new_unary_test(name)
        next_test.func_name = func_name
        locals()[func_name] = next_test
        del next_test
        
    for name in ll_math.binary_math_functions:
        func_name = 'test_%s' % (name,)
        next_test = new_binary_test(name)
        next_test.func_name = func_name
        locals()[func_name] = next_test
        del next_test
    
    def test_ldexp(self):
        def f(x, y):
            return math.ldexp(x, y)

        assert self.interpret(f, [3.4, 2]) == f(3.4, 2)
        # underflows give 0.0 with no exception raised
        assert f(1.0, -10000) == 0.0     # sanity-check the host Python
        assert self.interpret(f, [1.0, -10000]) == 0.0
