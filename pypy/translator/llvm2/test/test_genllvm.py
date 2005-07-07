from __future__ import division

import sys
import py

from pypy.rpython.rarithmetic import r_uint
from pypy.translator.llvm2.genllvm import compile_function

py.log.setconsumer("genllvm", py.log.STDOUT)
py.log.setconsumer("genllvm database prepare", None)

def test_return1():
    def simple1():
        return 1
    f = compile_function(simple1, [])
    assert f() == 1

def DONTtest_simple_function_pointer(): 
    def f1(x): 
        return x + 1
    def f2(x): 
        return x + 2

    l = [f1, f2]

    def pointersimple(i): 
        return l[i]

    f = compile_function(pointersimple, [int])
    assert f 

def test_simple_branching():
    def simple5(b):
        if b:
            x = 12
        else:
            x = 13
        return x
    f = compile_function(simple5, [bool])
    assert f(True) == 12
    assert f(False) == 13

def test_int_ops():
    def ops(i):
        x = 0
        x += i < i
        x += i <= i
        x += i == i
        x += i != i
        x += i >= i
        x += i > i
        x += x % i
        #x += i is not None
        #x += i is None
        return i + 1 * i // i - 1
    f = compile_function(ops, [int])
    assert f(1) == 1
    assert f(2) == 2
    
def test_while_loop():
    def factorial(i):
        r = 1
        while i>1:
            r *= i
            i -= 1
        return r
    f = compile_function(factorial, [int])
    assert factorial(4) == 24
    assert factorial(5) == 120
    f = compile_function(factorial, [float])
    assert factorial(4.) == 24.
    assert factorial(5.) == 120.

def test_return_void():
    def return_void(i):
        return None
    def call_return_void(i):
        return_void(i)
        return 1
    f = compile_function(call_return_void, [int])
    assert f(10) == 1

def test_break_while_loop():
    def factorial(i):
        r = 1
        while 1:
            if i<=1:
                break
            r *= i
            i -= 1
        return r
    f = compile_function(factorial, [int])
    assert factorial(4) == 24
    assert factorial(5) == 120


def test_primitive_is_true():
    def var_is_true(v):
        return bool(v)
    f = compile_function(var_is_true, [int])
    assert f(256)
    assert not f(0)
    f = compile_function(var_is_true, [r_uint])
    assert f(r_uint(256))
    assert not f(r_uint(0))
    f = compile_function(var_is_true, [float])
    assert f(256.0)
    assert not f(0.0)


def test_uint_ops():
    def ops(i):
        x = r_uint(0)
        x += i < i
        x += i <= i
        x += i == i
        x += i != i
        x += i >= i
        x += i > i
        x += x % i
        #x += i is not None
        #x += i is None
        return i + 1 * i // i - 1
    f = compile_function(ops, [r_uint])
    assert f(1) == 1
    assert f(2) == 2

def test_float_ops():
    def ops(flt):
        x = 0
        x += flt < flt
        x += flt <= flt
        x += flt == flt
        x += flt != flt
        x += flt >= flt
        x += flt > flt
        #x += flt fs not None
        #x += flt is None
        return flt + 1 * flt / flt - 1
    f = compile_function(ops, [float])
    assert f(1) == 1
    assert f(2) == 2


def test_function_call():
    def callee():
        return 1
    def caller():
        return 3 + callee()
    f = compile_function(caller, [])
    assert f() == 4

def test_recursive_call():
    def call_ackermann(n, m):
        return ackermann(n, m)
    def ackermann(n, m):
        if n == 0:
            return m + 1
        if m == 0:
            return ackermann(n - 1, 1)
        return ackermann(n - 1, ackermann(n, m - 1))
    f = compile_function(call_ackermann, [int, int])
    assert f(0, 2) == 3
    
def test_tuple_getitem(): 
    def tuple_getitem(i): 
        l = (4,5,i)
        return l[1]
    f = compile_function(tuple_getitem, [int])
    assert f(1) == tuple_getitem(1)

def test_nested_tuple():
    def nested_tuple(i): 
        l = (1,(1,2,i),i)
        return l[1][2]
    f = compile_function(nested_tuple, [int])
    assert f(4) == 4

def test_prebuilt_tuples():
    t1 = (1,2,3,4)
    t2 = (5,6,7,8)
    def callee_tuple(t):
        return t[0]
    def caller_tuple(i):
        if i:
            return callee_tuple(t1) + i
        else:
            return callee_tuple(t2) + i
    f = compile_function(caller_tuple, [int])
    assert f(0) == 5
    assert f(1) == 2

def test_pbc_fns(): 
    def f2(x):
         return x+1
    def f3(x):
         return x+2
    def g(y):
        if y < 0:
            f = f2
        else:
            f = f3
        return f(y+3)
    f = compile_function(g, [int])
    assert f(-1) == 3
    assert f(0) == 5

def DONTtest_simple_chars():
     def char_constant2(s):
         s = s + s + s
         return len(s + '.')
     def char_constant():
         return char_constant2("kk")    
     f = compile_function(char_constant, [])
     assert f() == 7

def test_list_getitem(): 
    def list_getitem(i): 
        l = [1,2,i+1]
        return l[i]
    f = compile_function(list_getitem, [int])
    assert f(0) == 1
    assert f(1) == 2
    assert f(2) == 3

def test_list_list_getitem(): 
    def list_list_getitem(): 
        l = [[1]]
        return l[0][0]
    f = compile_function(list_list_getitem, [])
    assert f() == 1

def test_list_getitem_pbc(): 
    l = [1,2]
    def list_getitem_pbc(i): 
        return l[i]
    f = compile_function(list_getitem_pbc, [int])
    assert f(0) == 1
    assert f(1) == 2
    
def test_list_list_getitem_pbc(): 
    l = [[0, 1], [0, 1]]
    def list_list_getitem_pbc(i): 
        return l[i][i]
    f = compile_function(list_list_getitem_pbc, [int])
    assert f(0) == 0
    assert f(1) == 1

def test_list_basic_ops(): 
    def list_basic_ops(i, j): 
        l = [1,2,3]
        l.insert(0, 42)
        del l[1]
        l.append(i)
        listlen = len(l)
        l.extend(l) 
        del l[listlen:]
        l += [5,6]
        l[1] = i
        return l[j]
    f = compile_function(list_basic_ops, [int, int])
    for i in range(6): 
        for j in range(6): 
            assert f(i,j) == list_basic_ops(i,j)

def test_string_simple(): 
    def string_simple(i): 
        return ord(str(i))
    f = compile_function(string_simple, [int], view=False)
    assert f(0) 
    
def test_string_simple_ops(): 
    def string_simple_ops(i): 
        res = 0
        s = str(i)
        s2 = s + s + s + s
        s3 = s + s + s + s
        res += s != s2
        res += s2 == s3
        res += ord(s)
        return res
    f = compile_function(string_simple_ops, [int])
    assert f(5) == ord('5') + 2
        

def DONTtest_string_getitem1():
    l = "Hello, World"
    def string_getitem1(i): 
        return l[i]
    f = compile_function(string_getitem1, [int], view=True)
    assert f(0) == ord("H")

def DONTtest_string_getitem2():
    def string_test(i): 
        l = "Hello, World"
        return l[i]
    f = compile_function(string_test, [int])
    assert f(0) == ord("H")

class TestException(Exception):
    pass

def DONTtest_exception():
    def raise_(i):
        if i:
            raise TestException()
        else:
            return 1
    def catch(i):
        try:
            return raise_(i)
        except TestException:
            return 0
    f = compile_function(catch, [int])
