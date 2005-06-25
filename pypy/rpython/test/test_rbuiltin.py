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

def test_int_max():
    def fn(i, j):
        return max(i,j)
    ev_fun = make_interpreter(fn, [0, 0])
    assert ev_fun(1, 2) == 2
    assert ev_fun(1, -1) == 1
    assert ev_fun(2, 2) == 2
    assert ev_fun(-1, -12) == -1

def test_builtin_math_floor():
    import math
    def fn(f):
        
        return math.floor(f)
    ev_fun = make_interpreter(fn, [0.0])
    import random 
    for i in range(20):
        rv = 1000 * float(i-10) #random.random()
        assert math.floor(rv) == ev_fun(rv)
        
def test_builtin_math_fmod():
    import math
    def fn(f,y):
        
        return math.fmod(f,y)
    ev_fun = make_interpreter(fn, [0.0,0.0])
    for i in range(20):
        for j in range(20):
            rv = 1000 * float(i-10) 
            ry = 100 * float(i-10) +0.1
            assert math.fmod(rv,ry) == ev_fun(rv,ry)        
##import time
##def test_time_time():            
##    def f(neg):
##        if neg:
##            return time.time()
##        else:
##            return time.clock()
##    ev_fn = make_interpreter(f,[True])
##    assert isinstance(ev_fn(True),float)
##    assert isinstance(ev_fn(False),float)
    
    