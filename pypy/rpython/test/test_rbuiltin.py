from pypy.rpython.test.test_llinterp import interpret

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
    ev_fun = interpret(fn, [0, 0])
    assert interpret(fn, (1, 2)) == 1
    assert interpret(fn, (1, -1)) == -1
    assert interpret(fn, (2, 2)) == 2
    assert interpret(fn, (-1, -12)) == -12

def test_int_max():
    def fn(i, j):
        return max(i,j)
    assert interpret(fn, (1, 2)) == 2
    assert interpret(fn, (1, -1)) == 1
    assert interpret(fn, (2, 2)) == 2
    assert interpret(fn, (-1, -12)) == -1

def test_builtin_math_floor():
    import math
    def fn(f):
        return math.floor(f)
    import random 
    for i in range(5):
        rv = 1000 * float(i-10) #random.random()
        res = interpret(fn, [rv])
        assert fn(rv) == res 
        
def test_builtin_math_fmod():
    import math
    def fn(f,y):
        return math.fmod(f,y)

    for i in range(10):
        for j in range(10):
            rv = 1000 * float(i-10) 
            ry = 100 * float(i-10) +0.1
            assert fn(rv,ry) == interpret(fn, (rv, ry))

def test_pbc_isTrue():
    class C:
        def f(self):
            pass
        
    def g(obj):
        return bool(obj)
    def fn(neg):    
        c = C.f
        return g(c)
    assert interpret(fn, [True])
    def fn(neg):    
        c = None
        return g(c)
    assert not interpret(fn, [True]) 
    
