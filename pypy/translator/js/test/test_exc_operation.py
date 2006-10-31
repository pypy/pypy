import py
import sys
from pypy.translator.js.test.runtest import compile_function
from pypy.rlib.rarithmetic import r_uint, ovfcheck, ovfcheck_lshift
from pypy.translator.test import snippet 

py.test.skip("Exception work in progress")

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

def DONTtest_neg_int_ovf(): #issue with Javascript Number() having a larger range
    def neg_int_ovf(n):
        try:
            r=ovfcheck(-n)
        except OverflowError:
            return 123
        return r
    f = compile_function(neg_int_ovf, [int])
    for i in (-sys.maxint-1, -sys.maxint, 0, sys.maxint-1, sys.maxint):
        assert f(i) == neg_int_ovf(i)

def DONTtest_abs_int_ovf(): #issue with Javascript Number() having a larger range
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

#raises(...) fails because we do'nt reraise javascript exceptions on the python level

def DONTtest_int_ovf(): #issue with Javascript Number() having a larger range
    def int_ovf_fn(i):
        try:
            return snippet.add_func(i)
        except OverflowError:
            return 123
        except:
            return 1234
    fn = compile_function(int_ovf_fn, [int])
    for i in (-sys.maxint-1, -1, 0, 1, sys.maxint):
        assert fn(i) == int_ovf_fn(i)

def test_int_div_ovf_zer():
    def int_div_ovf_zer_fn(i):
        try:
            return snippet.div_func(i)
        except OverflowError:
            return 123
        except ZeroDivisionError:
            return 1234
        except:
            return 12345
    fn = compile_function(int_div_ovf_zer_fn, [int])
    for i in (-sys.maxint-1, -1, 0, 1, sys.maxint):
        assert fn(i) == int_div_ovf_zer_fn(i)

def DONTtest_int_mod_ovf_zer(): #issue with Javascript Number() having a larger range
    def int_mod_ovf_zer_fn(i):
        try:
            return snippet.mod_func(i)
        except OverflowError:
            return 123
        except ZeroDivisionError:
            return 1234
        except:
            return 12345
    fn = compile_function(int_mod_ovf_zer_fn, [int])
    for i in (-sys.maxint-1, -1, 0, 1, sys.maxint):
        assert fn(i) == int_mod_ovf_zer_fn(i)

def DONTtest_int_rshift_val():  #issue with Javascript Number() having a larger range
    def rshift_fn(i):
        try:
            return snippet.rshift_func(i)
        except ValueError:
            return 123
        except:
            return 1234
    fn = compile_function(rshift_fn, [int])
    for i in (-sys.maxint-1, -1, 0, 1, sys.maxint):
        assert fn(i) == rshift_fn(i)

def test_int_lshift_ovf_val():
    def lshift_fn(i):
        try:
            return snippet.lshift_func(i)
        except ValueError:
            return 123
        except OverflowError:
            return 1234
        except:
            return 12345
    fn = compile_function(lshift_fn, [int])
    for i in (-sys.maxint-1, -1, 0, 1, sys.maxint):
        assert fn(i) == lshift_fn(i)

def test_uint_arith():
    py.test.skip("unsigned number becomes negative because we should cast to unsigned when necessary")
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
            return ovfcheck(i - 1)
        except OverflowError:
            return 123
    n_ovf = 0
    f = compile_function(sub_func, [int])
    for i in (-1, 0, 1, sys.maxint, -sys.maxint, -sys.maxint-1):
        result = f(i)
        assert result == sub_func(i)
        n_ovf += result == 123
    assert n_ovf == 1

#As JavaScript uses floating-point numbers the accuracy is only assured
#for integers between: -9007199254740992 (-2^53) and 9007199254740992 (2^53)
def DONTtest_shift_with_overflow(): #issue with Javascript Number() having a larger range
    def shiftleft(x, y):
        return x << y
    def shiftright(x, y):
        return x >> y
    shl = compile_function(shiftleft , [int, int])
    shr = compile_function(shiftright, [int, int])
    for i in [1, 2, 3, 100000, 2000000, sys.maxint - 1]:
        for j in [1, 2, 3, 100000, 2000000, sys.maxint - 1]:
            assert shl(i, j) == i << j
            assert shr(i, j) == i >> j
