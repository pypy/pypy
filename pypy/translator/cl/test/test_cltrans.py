import autopath
import py 
import os

from pypy.annotation.model import SomeChar
from pypy.translator.cl.buildcl import make_cl_func

from pypy.translator.test import snippet as t

def dont_test_return_str():
    def return_str():
        return 'test'
    cl_return_str = make_cl_func(return_str)
    assert cl_return_str() == 'test'

def test_chr_ord():
    def chr_ord(num):
        char = chr(num)
        return ord(char)
    cl_chr_ord = make_cl_func(chr_ord, [int])
    assert cl_chr_ord(32) == 32
    def ord_chr(char):
        num = ord(char)
        return chr(num)
    cl_ord_chr = make_cl_func(ord_chr, [SomeChar()])
    assert cl_ord_chr('a') == 'a'

def test_float_int():
    def cast_float(num):
        return float(num)
    cl_cast_float = make_cl_func(cast_float, [int])
    assert cl_cast_float(1) == 1.0
    def cast_int(num):
        return int(num)
    cl_cast_int = make_cl_func(cast_int, [float])
    assert cl_cast_int(1.0) == 1
    assert cl_cast_int(1.5) == 1
    assert cl_cast_int(-1.5) == -1

def test_int_div():
    def int_div(a, b):
        return a / b
    cl_int_div = make_cl_func(int_div, [int, int])
    assert cl_int_div(4, 2) == 2
    assert cl_int_div(5, 2) == 2
    assert cl_int_div(4, -2) == -2
    assert cl_int_div(5, -2) == -3

def test_range():
    def get_three():
        lst = range(7)
        return lst[3]
    cl_get_three = make_cl_func(get_three)
    assert cl_get_three() == 3

def test_if():
    cl_if = make_cl_func(t.if_then_else, [bool, int, int])
    assert cl_if(True, 50, 100) == 50
    assert cl_if(False, 50, 100) == 100
    cl_if = make_cl_func(t.if_then_else, [int, int, int])
    assert cl_if(0, 50, 100) == 100
    assert cl_if(1, 50, 100) == 50

def test_gcd():
    cl_gcd = make_cl_func(t.my_gcd, [int, int])
    assert cl_gcd(96, 64) == 32

def test_is_perfect(): # pun intended
    cl_perfect = make_cl_func(t.is_perfect_number, [int])
    assert cl_perfect(24) == False
    assert cl_perfect(28) == True

def test_bool():
    cl_bool = make_cl_func(t.my_bool, [int])
    assert cl_bool(0) == False
    assert cl_bool(42) == True
    cl_bool = make_cl_func(t.my_bool, [bool])
    assert cl_bool(True) == True

def test_contains():
    def contains_int(num):
        return t.my_contains([1,2,3], num)
    my_contains = make_cl_func(contains_int, [int])
    assert my_contains(1)
    assert not my_contains(0)
    is_one_or_two = make_cl_func(t.is_one_or_two, [int])
    assert is_one_or_two(2)
    assert not is_one_or_two(3)

def test_array():
    py.test.skip("temporarily disabled")
    cl_four = make_cl_func(t.two_plus_two)
    assert cl_four() == 4

def test_sieve():
    py.test.skip("temporarily disabled")
    cl_sieve = make_cl_func(t.sieve_of_eratosthenes)
    assert cl_sieve() == 1028

def test_easy():
    # These are the Pyrex tests which were easy to adopt.
    f1 = make_cl_func(t.simple_func, [int])
    assert f1(1) == 2
    f2 = make_cl_func(t.while_func, [int])
    assert f2(10) == 55
    f3 = make_cl_func(t.simple_id, [int])
    assert f3(9) == 9
    f4 = make_cl_func(t.branch_id, [int, int, int])
    assert f4(1, 2, 3) == 2
    assert f4(0, 2, 3) == 3
    f5 = make_cl_func(t.int_id, [int])
    assert f5(3) == 3
    f6 = make_cl_func(t.time_waster, [int])
    assert f6(30) == 3657

def test_string():
    py.test.skip("strings not supported")
    cl_greet = make_cl_func(t.greet, [str])
    assert cl_greet("world") == "helloworld"
    cl_stringmaker = make_cl_func(t.nested_whiles, [int, int])
    assert cl_stringmaker(111, 114) == (
                      "...!...!...!...!...!")

def test_for():
    py.test.skip("strings not supported")
    cl_python = make_cl_func(t.choose_last)
    assert cl_python() == "python"

def test_builtin():
    cl_builtinusage = make_cl_func(t.builtinusage)
    assert cl_builtinusage() == 4

def test_slice():
    py.test.skip("either this is not RPython or gencl has something horribly wrong")
    cl_half = make_cl_func(t.half_of_n, [int])
    assert cl_half(10) == 5

def test_powerset():
    py.test.skip("another test that fails in the rtyper, not RPython?")
    cl_powerset = make_cl_func(t.powerset, [int])
    result = cl_powerset(3)
    assert result.__class__ == Literal
    assert result.val == (
                      '#(#() #(0) #(1) #(0 1) #(2) #(0 2) #(1 2) #(0 1 2))')
def test_yast():
    def yast1(n):
        # Need this to avoid name clashes in the generated code
        return t.yast(range(n))
    cl_sum = make_cl_func(yast1, [int]) # yet another sum test
    assert cl_sum(12) == 66

def test_name_clash():
    py.test.skip("Name clash between the 2 yast functions")
    def yast(n):
        return t.yast(range(n))
    cl_sum = make_cl_func(yast, [int])
    assert cl_sum(12) == 66

def test_int_add():
    def add_two(number):
        return number + 2
    cl_add_two = make_cl_func(add_two, [int])
    assert cl_add_two(5) == 7


# TODO
# poor_man_range
# - append/reverse. not RPython. delegate?
# attrs
# - attribute. need object. symbol-plist?
