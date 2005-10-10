import py
import sys
from pypy.translator.js.test.runtest import compile_function
from pypy.rpython.rarithmetic import r_uint, ovfcheck, ovfcheck_lshift
from pypy.translator.test import snippet 

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

############################

def test_int_overflow():
    py.test.skip("ovf operator exception not implemented")
    fn = compile_function(snippet.add_func, [int])
    raises(OverflowError, fn, sys.maxint)

def test_int_div_ovf_zer():
    py.test.skip("ovf_zer operator exception not implemented")
    fn = compile_function(snippet.div_func, [int])
    raises(OverflowError, fn, -1)
    raises(ZeroDivisionError, fn, 0)

def test_int_mod_ovf_zer():
    py.test.skip("ovf_zer operator exception not implemented")
    fn = compile_function(snippet.mod_func, [int])
    raises(OverflowError, fn, -1)
    raises(ZeroDivisionError, fn, 0)

def test_int_rshift_val():
    py.test.skip("val operator exception not implemented")
    fn = compile_function(snippet.rshift_func, [int])
    raises(ValueError, fn, -1)

def test_int_lshift_ovf_val():
    py.test.skip("ovf_val operator exception not implemented")
    fn = compile_function(snippet.lshift_func, [int])
    raises(ValueError, fn, -1)
    raises(OverflowError, fn, 1)

def test_uint_arith():
    py.test.skip("zer operator exception not implemented")
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
    py.test.skip("ovf operator exception not implemented")
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
    py.test.skip("ovf operator exception not implemented")
    def sub_func(i):
        try:
            return ovfcheck(i - 1)
        except OverflowError:
            return 123
    f = compile_function(sub_func, [int])
    assert f(0) == sub_func(0)
    assert f(0) == 1
    assert f(sys.maxint) == sub_func(sys.maxint)
    assert f(sys.maxint) == 123

def test_shift_with_overflow():
    py.test.skip("shift operator exception not implemented")
    shl = compile_function(llvmsnippet.shiftleft, [int, int])
    shr = compile_function(llvmsnippet.shiftright, [int, int])
    for i in [1, 2, 3, 100000, 2000000, sys.maxint - 1]:
        for j in [1, 2, 3, 100000, 2000000, sys.maxint - 1]:
            assert shl(i, j) == i << j
            assert shr(i, j) == i >> j
