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
