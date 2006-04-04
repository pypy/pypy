import py
from pypy.rpython.test.test_llinterp import interpret 
from pypy.rpython.ootypesystem.ootype import *

def test_new():
    LT = List(Signed)
    l = new(LT)
    assert typeOf(l) == LT

def test_len():
    LT = List(Signed)
    l = new(LT)
    assert l.length() == 0

def test_append():
    LT = List(Signed)
    l = new(LT)
    l.append(1)
    assert l.length() == 1

def test_setitem_getitem():
    LT = List(Signed)
    l = new(LT)
    l.append(2)
    assert l.getitem(0) == 2
    l.setitem(0, 3)
    assert l.getitem(0) == 3

def test_setitem_indexerror():
    LT = List(Signed)
    l = new(LT)
    py.test.raises(IndexError, l.getitem, 0)
    py.test.raises(IndexError, l.setitem, 0, 1)

class TestInterpreted:

    def test_append_length(self):
        def f(x):
            l = []
            l.append(x)
            return len(l)
        res = interpret(f, [2], type_system="ootype")
        assert res == 1 

    def test_setitem_getitem(self):
        def f(x):
            l = []
            l.append(3)
            l[0] = x
            return l[0]
        res = interpret(f, [2], type_system="ootype")
        assert res == 2 

