import py
from pypy.rpython.test.test_llinterp import interpret
from pypy.rpython.objectmodel import r_dict

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

def test_unichar_dict():
    d = {u'a': 5, u'b': 123, u'?': 321}
    def func(i):
        return d[unichr(i)]
    res = interpret(func, [97])
    assert res == 5
    res = interpret(func, [98])
    assert res == 123
    res = interpret(func, [63])
    assert res == 321

def test_constant_r_dict():
    def strange_key_eq(key1, key2):
        return key1[0] == key2[0]   # only the 1st character is relevant
    def strange_key_hash(key):
        return ord(key[0])

    d = r_dict(strange_key_eq, strange_key_hash)
    d['hello'] = 42
    d['world'] = 43
    def func(i):
        return d[chr(i)]
    res = interpret(func, [ord('h')])
    assert res == 42
    res = interpret(func, [ord('w')])
    assert res == 43
