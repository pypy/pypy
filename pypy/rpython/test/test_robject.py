from pypy.rpython.lltypesystem.lltype import *
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
    res = interpret(f, [2, 'c'], someobjects=True)
    assert res == 4
    res = interpret(f, [3, 'c'], someobjects=True)
    assert res == 4

def test_obj_list():
    def f(i, c):
        lis = [1, 2, 3, 4]
        lis[i] = c
        lis.append(i)
        return len(lis)
    res = interpret(f, [2, 'c'], someobjects=True)
    assert res == 5
    res = interpret(f, [3, 'c'], someobjects=True)
    assert res == 5

def test_obj_iter():
    def f(flag):
        if flag:
            x = (1, 2)
        else:
            x = '34'
        lst = [u for u in x]
        return lst[flag]
    res = interpret(f, [1], someobjects=True)
    assert res._obj.value == 2
    res = interpret(f, [0], someobjects=True)
    assert res._obj.value == '3'

def test_listofobj_iter():
    def f(look):
        lst = ['*', 2, 5]
        for u in lst:
            if u == look:
                return True
        return False
    res = interpret(f, [1], someobjects=True)
    assert res is False
    res = interpret(f, [2], someobjects=True)
    assert res is True
