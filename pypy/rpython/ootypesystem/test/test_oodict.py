import py
from pypy.rpython.test.test_llinterp import interpret 
from pypy.rpython.ootypesystem.ootype import Signed, Float, Dict, new, typeOf

def test_new():
    DT = Dict(Signed, Float)
    d = new(DT)
    assert typeOf(d) == DT

def test_length():
    DT = Dict(Signed, Float)
    d = new(DT)
    d.ll_setitem(42, 123.45)
    assert d.ll_length() == 1

def test_setitem_getitem():
    DT = Dict(Signed, Float)
    d = new(DT)
    d.ll_setitem(42, 123.45)
    assert d.ll_getitem(42) == 123.45
