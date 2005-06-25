from pypy.rpython.test.test_llinterp import interpret, make_interpreter
from pypy.annotation.builtin import *
import py

def test_rbuiltin_list():
    def f(): 
        l=list((1,2,3))
        return l == [1,2,3]
    def g():
        l=list(('he','llo'))
        return l == ['he','llo']
    def r():
        l = ['he','llo']
        l1=list(l)
        return l == l1 and l is not l1
    result = interpret(f,[])
    assert result
    
    result = interpret(g,[])
    assert result
    
    result = interpret(r,[])
    assert result    
    
def test_int_min():
    def fn(i, j):
        return min(i,j)
    ev_fun = make_interpreter(fn, [0, 0])
    assert ev_fun(1, 2) == 1
    assert ev_fun(1, -1) == -1
    assert ev_fun(2, 2) == 2
    assert ev_fun(-1, -12) == -12

def test_int_min():
    def fn(i, j):
        return min(i,j)
    ev_fun = make_interpreter(fn, [0, 0])
    assert ev_fun(1, 2) == 1
    assert ev_fun(1, -1) == -1
    assert ev_fun(2, 2) == 2
    assert ev_fun(-1, -12) == -12
