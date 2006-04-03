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


class TestInterpreted:

    def test_append_length(self):
        def f(x):
            l = []
            l.append(x)
            return len(l)
        res = interpret(f, [2], type_system="ootype")
        assert res == 1 
