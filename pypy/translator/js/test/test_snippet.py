from __future__ import division

from pypy.translator.js.test.runtest import compile_function
from pypy.translator.test import snippet as test

import py

class TestSnippet(object):
    def test_if_then_else(self):
        f = compile_function(test.if_then_else, [int, int, int])
        assert f(0, 12, 13) == 13
        assert f(13, 12, 13) == 12
        
    def test_my_gcd(self):
        f = compile_function(test.my_gcd, [int, int])
        assert f(15, 5) == 5
        assert f(18, 42) == 6

    def test_is_perfect_number(self):
        f = compile_function(test.is_perfect_number, [int])
        assert f(28) == 1
        assert f(123) == 0
        assert f(496) == 1

    def test_my_bool(self):
        f = compile_function(test.my_bool, [int])
        assert f(10) == 1
        assert f(1) == 1
        assert f(0) == 0

    def test_two_plus_two(self):
        f = compile_function(test.two_plus_two, [])
        assert f() == 4

    def test_sieve_of_eratosthenes(self):
        #py.test.skip("Loop error in loop detection software")
        f = compile_function(test.sieve_of_eratosthenes, [])
        assert f() == 1028
    
    def test_nested_whiles(self):
        #py.test.skip("Loop error in loop detection software")
        f = compile_function(test.nested_whiles, [int, int])
        assert test.nested_whiles(3,2) == f(3,2)

    def test_simple_func(self):
        f = compile_function(test.simple_func, [int])
        assert f(1027) == 1028
        
    def test_while_func(self):
        while_func = compile_function(test.while_func, [int])
        assert while_func(10) == 55

    def test_time_waster(self):
        #py.test.skip("Loop error in loop detection software")
        f = compile_function(test.time_waster, [int])
        assert f(1) == 1
        assert f(2) == 2
        assert f(3) == 6
        assert f(4) == 12

    def test_int_id(self):
        f = compile_function(test.int_id, [int])
        assert f(1027) == 1027

    def test_factorial2(self):
        #py.test.skip("unknown error")
        factorial2 = compile_function(test.factorial2, [int])
        assert factorial2(5) == 120

    def test_factorial(self):
        #py.test.skip("unknown error")
        factorial = compile_function(test.factorial, [int])
        assert factorial(5) == 120

    def test_set_attr(self):
        set_attr = compile_function(test.set_attr, [])
        assert set_attr() == 2

    def test_merge_setattr(self):
        merge_setattr = compile_function(test.merge_setattr, [bool])
        assert merge_setattr(1) == 1

    def test_simple_method(self):
        simple_method = compile_function(test.simple_method, [int])
        assert simple_method(65) == 65

    def test_with_init(self):
        with_init = compile_function(test.with_init, [int])
        assert with_init(42) == 42

    def test_with_more_init(self):
        with_more_init = compile_function(test.with_more_init, [int, bool])
        assert with_more_init(42, True) == 42
        assert with_more_init(42, False) == -42
