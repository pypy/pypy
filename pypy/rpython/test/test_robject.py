from pypy.translator.translator import Translator
from pypy.rpython.lltype import *
from pypy.rpython.test.test_llinterp import interpret


def test_simple():
    def fn(obj):
        return obj + 1
    _1L = pyobjectptr(1L)
    res = interpret(fn, [_1L], someobjects=True)
    assert res._obj.value == 2L

def test_obj_obj_dict():
    def f(i, c):
        d = {}
        d[1] = 'a'
        d['a'] = i
        d['ab'] = c
        d[i] = c
        return len(d)
    res = interpret(f, [2, 'c'])
    assert res == 4
    res = interpret(f, [3, 'c'])
    assert res == 4

def test_obj_list():
    def f(i, c):
        lis = [1, 2, 3, 4]
        lis[i] = c
        return len(lis)
    res = interpret(f, [2, 'c'])#, view=True)
    assert res == 4
    res = interpret(f, [3, 'c'])
    assert res == 4
