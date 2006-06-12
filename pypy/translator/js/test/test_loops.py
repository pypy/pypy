import py

from pypy.translator.js.test.runtest import compile_function 

import sys

def test_if_simple():
    def f(x):
        if x == 1:
            return 1
        else:
            return 2
    fn = compile_function(f,[int])
    assert fn(1) == f(1)
    assert fn(2) == f(2)

def test_if_call():
    def check(x):
        if x == 1:
            return True
        return False
    
    def f(x):
        if check(x):
            return 1
        else:
            return 2
        
    fn = compile_function(f,[int])
    assert fn(1) == f(1)
    assert fn(2) == f(2)

def test_while():
    def f(s):
        while s > 1:
            s -= 1
        return s
    
    fn = compile_function(f,[int])
    assert fn(38) == f(38)
    assert fn(5) == f(5)

def test_while_break():
    def f(s):
        while s > 1:
            if s == 8:
                break
            s -= 1
        return s
    
    fn = compile_function(f,[int])
    assert fn(38) == f(38)
    assert fn(5) == f(5)

def test_while_if():
    def f(x):
        while x > 1:
            if x%2 == 0:
                x -= 7
            else:
                x -= 3
        return x
    
    fn = compile_function(f,[int])
    assert fn(38) == f(38)
    assert fn(5) == f(5)
