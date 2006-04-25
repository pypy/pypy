from pypy.rpython.ootypesystem.ootype import *

def test_type_comparison():
    T = Tuple({"a": Signed, "b": Signed})
    T2 = Tuple({"a": Signed, "b": Signed})
    T3 = Tuple({"a": Signed, "b": Unsigned})

    assert T == T2
    assert T2 != T3
    assert hash(T) == hash(T2)

def test_new():
    T = Tuple({"a": Signed, "b": Signed})
    t = new(T)
    assert t.a == 0
    assert t.b == 0

def test_getsetitem():
    T = Tuple({"a": Signed, "b": Signed})
    t = new(T)
    t.a = 2
    t.b = 3
    assert t.a == 2
    assert t.b == 3

def test_null():
    T = Tuple({"a": Signed})
    n = null(T)
    n2 = null(T)
    assert n == n2

def test_ooidentityhash():
    T = Tuple({"a": Signed, "b": Signed})
    t = new(T)
    t.a = 1
    t.b = 2
    t2 = new(T)
    t.a = 1
    t.b = 2
    assert ooidentityhash(t) != ooidentityhash(t2)
