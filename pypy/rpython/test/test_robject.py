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
        return d
    res = interpret(f, [1, 'c'])
    print res
    
