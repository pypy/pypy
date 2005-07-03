import py
from pypy.rpython.test.test_llinterp import interpret 

def test_constant_int_dict(): 
    d = {1: 2, 2: 3, 3: 4} 
    def func(i): 
        return d[i]
    res = interpret(func, [3])
    assert res == 4

def test_constantdict_contains():
    d = {1: True, 4: True, 16: True}
    def func(i):
        return i in d
    res = interpret(func, [15])
    assert res is False
    res = interpret(func, [4])
    assert res is True

def test_constantdict_get():
    d = {1: -11, 4: -44, 16: -66}
    def func(i, j):
        return d.get(i, j)
    res = interpret(func, [15, 62])
    assert res == 62
    res = interpret(func, [4, 25])
    assert res == -44
