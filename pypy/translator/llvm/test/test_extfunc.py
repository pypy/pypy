from __future__ import division

import os
import sys

import py

from pypy.translator.llvm.test.runtest import *

def test_external_function_ll_time_time():
    import time
    def fn():
        return time.time()
    f = compile_function(fn, [])
    assert abs(f()-fn()) < 10.0

def test_external_function_ll_time_clock():
    import time
    def fn():
        return time.clock()
    f = compile_function(fn, [], isolate_hint=False)
    assert abs(f()-fn()) < 10.0

def test_math_frexp():
    if sys.maxint != 2**31-1:
        py.test.skip("WIP on 64 bit architectures") 

    from math import frexp
    def fn(x):
        res = frexp(x)
        return res[0] + float(res[1])
    f = compile_function(fn, [float])
    res = f(10.123)
    assert res == fn(10.123)

def test_math_modf():
    from math import modf
    def fn(x):
        res = modf(x)
        return res[0] + res[1]
    f = compile_function(fn, [float])
    assert f(10.123) == fn(10.123)

simple_math_functions = [
    'acos', 'asin', 'atan', 'ceil', 'cos', 'cosh', 'exp', 'fabs',
    'floor', 'log', 'log10', 'sin', 'sinh', 'sqrt', 'tan', 'tanh'
    ]

def math_function_test(funcname):
    import random
    import math
    mathfn = getattr(math, funcname)
    print funcname, 
    def fn(x):
        return mathfn(x)
    f = compile_function(fn, [float])
    for x in [0.12334, 0.3, 0.5, 0.9883]:
        print x
        assert f(x) == mathfn(x)

def test_simple_math_functions():
    for funcname in simple_math_functions:
        yield math_function_test, funcname

def test_rarith_parts_to_float():
    if sys.maxint != 2**31-1:
        py.test.skip("WIP on 64 bit architectures") 
    from pypy.rlib.rarithmetic import parts_to_float
    parts = [
     ["" ,"1","" ,""],
     ["-","1","" ,""],
     ["-","1","5",""],
     ["-","1","5","2"],
     ["-","1","5","+2"],
     ["-","1","5","-2"],
    ]
    val = [1.0, -1.0, -1.5, -1.5e2, -1.5e2, -1.5e-2]
    def fn(i):
        sign, beforept, afterpt, exponent = parts[i]
        return parts_to_float(sign, beforept, afterpt, exponent)
    f = compile_function(fn, [int])
    for i, v in enumerate(val):
        assert f(i) == v

def test_rarith_formatd():
    if sys.maxint != 2**31-1:
        py.test.skip("WIP on 64 bit architectures") 
    from pypy.rlib.rarithmetic import formatd
    as_float  = [ 0.0  ,  1.5  ,  2.0  ]
    as_string = ["0.00", "1.50", "2.00"]
    def fn(i):
        return formatd("%.2f", as_float[i]) == as_string[i]
    f = compile_function(fn, [int])
    for i, s in enumerate(as_string):
        assert f(i)

