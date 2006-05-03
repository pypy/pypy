import py
from pypy.rpython.test.test_llinterp import interpret 

def test_empty_dict():
    class A:
        pass
    a = A()
    a.d1 = {}
    def func():
        a.d2 = {}
        return bool(a.d1) or bool(a.d2)
    res = interpret(func, [])
    assert res is False

def test_iterate_over_empty_dict():
    def f():
        n = 0
        d = {}
        for x in []:                n += x
        for y in d:                 n += y
        for z in d.iterkeys():      n += z
        for s in d.itervalues():    n += s
        for t, u in d.items():      n += t * u
        for t, u in d.iteritems():  n += t * u
        return n
    res = interpret(f, [])
    assert res == 0
