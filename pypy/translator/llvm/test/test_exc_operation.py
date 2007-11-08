import sys

import py
from pypy.rlib.rarithmetic import r_uint, ovfcheck, ovfcheck_lshift
from pypy.translator.test import snippet 

from pypy.translator.llvm.test.runtest import *

def test_zerodiv_int():
    def zerodiv_int(n):
        try:
            r=100/n
        except ZeroDivisionError:
            return n+7
        return r
    f = compile_function(zerodiv_int, [int])
    for i in (-50,0,50):
        assert f(i) == zerodiv_int(i)

def test_zerodiv_uint():
    def zerodiv_uint(n):
        try:
            r=100/n
        except ZeroDivisionError:
            return n+7
        return r
    f = compile_function(zerodiv_uint, [r_uint])
    for i in (0,50,100):
        assert f(i) == zerodiv_uint(i)

def test_zerodivrem_int():
    def zerodivrem_int(n):
        try:
            r=100%n
        except ZeroDivisionError:
            return n+7
        return r
    f = compile_function(zerodivrem_int, [int])
    for i in (-50,0,50):
        assert f(i) == zerodivrem_int(i)

def test_zerodivrem_uint():
    def zerodivrem_uint(n):
        try:
            r=100%n
        except ZeroDivisionError:
            return n+7
        return r
    f = compile_function(zerodivrem_uint, [r_uint])
    for i in (0,50,100):
        assert f(i) == zerodivrem_uint(i)

def test_neg_int_ovf():
    def neg_int_ovf(n):
        try:
            r=ovfcheck(-n)
        except OverflowError:
            return 123
        return r
    f = compile_function(neg_int_ovf, [int])
    for i in (-sys.maxint-1, -sys.maxint, 0, sys.maxint-1, sys.maxint):
        assert f(i) == neg_int_ovf(i)

def test_abs_int_ovf():
    def abs_int_ovf(n):
        try:
            r=ovfcheck(abs(n))
        except OverflowError:
            return 123
        return r
    f = compile_function(abs_int_ovf, [int])
    for i in (-sys.maxint-1, -sys.maxint, 0, sys.maxint-1, sys.maxint):
        assert f(i) == abs_int_ovf(i)

def test_int_overflow():
    def fn(i):
        try:
            return snippet.add_func(i)
        except OverflowError:
            return 123
    f = compile_function(fn, [int])
    assert f(10) == 11
    assert f(sys.maxint) == 123

def test_int_div_ovf_zer():
    def fn(i):
        try:
            return snippet.div_func(i)
        except OverflowError:
            return 123
        except ZeroDivisionError:
            return 1234
        
    fn = compile_function(fn, [int])
    assert fn(-1) == 123
    assert fn(0) == 1234

def test_int_mod_ovf_zer():
    py.test.skip("XXX fix this : the wrong result is returned")
    def fn(i):
        try:
            return snippet.mod_func(i)
        except OverflowError:
            return 123
        except ZeroDivisionError:
            return 1234
            
    fn = compile_function(fn, [int])
    assert fn(0) == 1234
    assert fn(1) == 123

def test_int_rshift_val():
    def fn(i):
        try:
            return snippet.rshift_func(i)
        except ValueError:
            return 123
        
    f = compile_function(fn, [int])
    assert f(0) == -sys.maxint - 1
    assert f(-1) == 123

def test_int_lshift_ovf_val():
    def fn(i):
        try:
            return snippet.lshift_func(i)
        except ValueError:
            return 123
        except OverflowError:
            return 1234
        
    f = compile_function(fn, [int])
    assert f(0) == -sys.maxint-1
    assert f(-1) == 123
    assert f(1) == 1234

def test_uint_arith():
    def fn(i):
        try:
            return ~(i*(i+1))/(i-1)
        except ZeroDivisionError:
            return r_uint(91872331)
    f = compile_function(fn, [r_uint])
    for value in range(15):
        i = r_uint(value)
        assert f(i) == fn(i)

def test_int_add_ovf():
    def add_func(i):
        try:
            return ovfcheck(i + 1)
        except OverflowError:
            return 123
    f = compile_function(add_func, [int])
    assert f(0) == add_func(0)
    assert f(0) == 1
    assert f(sys.maxint) == add_func(sys.maxint)
    assert f(sys.maxint) == 123

def test_int_sub_ovf():
    def sub_func(i):
        try:
            return ovfcheck(i - 2)
        except OverflowError:
            return 123
    f = compile_function(sub_func, [int])
    assert f(0) == sub_func(0)
    assert f(sys.maxint) == sub_func(sys.maxint)
    assert f(-sys.maxint) == 123

def test_int_mul_ovf():
    #if sys.maxint != 2**31-1:
    #    py.test.skip("WIP on 64 bit architectures")
    def mul_func(i):
        try:
            return ovfcheck(i * 100)
        except OverflowError:
            return 123
    f = compile_function(mul_func, [int])
    assert f(0) == mul_func(0)
    assert f(567) == mul_func(567)
    assert f(sys.maxint) == 123
