import py
from pypy.rpython.test.test_llinterp import interpret 
from pypy.rpython.ootypesystem.ootype import Signed, Float, Dict, new, typeOf, setDictTypes

def test_new():
    DT = Dict(Signed, Float)
    d = new(DT)
    assert typeOf(d) == DT

def test_length():
    DT = Dict(Signed, Float)
    d = new(DT)
    d.ll_set(42, 123.45)
    assert d.ll_length() == 1

def test_setitem_getitem():
    DT = Dict(Signed, Float)
    d = new(DT)
    d.ll_set(42, 123.45)
    assert d.ll_contains(42)
    assert d.ll_get(42) == 123.45

def test_iteritems():
    DT = Dict(Signed, Float)
    d = new(DT)
    d.ll_set(42, 43.0)
    d.ll_set(52, 53.0)
    it = d.ll_get_items_iterator()
    items = []
    while it.ll_go_next():
        items.append((it.ll_current_key(), it.ll_current_value()))
    items.sort()
    assert items == [(42, 43.0), (52, 53.0)]

def test_optional_types():
    DT = Dict()
    DT2 = Dict(Signed, Float)
    assert DT != Signed
    assert DT != DT2
    assert DT2 != DT
    py.test.raises(TypeError, hash, DT)
    setDictTypes(DT, Signed, Float)
    assert DT == DT2
    assert DT2 == DT
    assert hash(DT) == hash(DT2)

def test_recursive_str_hash():
    DT = Dict()
    setDictTypes(DT, Signed, DT)
    assert isinstance(str(DT), str)
    assert isinstance(hash(DT), int)

def test_invalid_cache():
    DT = Dict(Signed, Signed)
    d = new(DT)
    py.test.raises(AssertionError, d.ll_get, 0)
    d.ll_set(42, 1)
    d.ll_contains(43)
    py.test.raises(AssertionError, d.ll_get, 42)
