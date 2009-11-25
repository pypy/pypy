from pypy.rpython.ootypesystem.ootype import *

def test_type_comparison():
    T = Record({"a": Signed, "b": Signed})
    T2 = Record({"a": Signed, "b": Signed})
    T3 = Record({"a": Signed, "b": Unsigned})

    assert T == T2
    assert T2 != T3
    assert hash(T) == hash(T2)

def test_value_comparison():
    T = Record({"a": Signed, "b": Signed})
    T2 = Record({"a": Signed, "b": Float})

    t = new(T)
    t.a = 0
    t.b = 0
    t2 = new(T2)
    t.a = 0
    t.b = 0.0
    assert T != T2
    assert t != t2

def test_new():
    T = Record({"a": Signed, "b": Signed})
    t = new(T)
    assert t.a == 0
    assert t.b == 0

def test_getsetitem():
    T = Record({"a": Signed, "b": Signed})
    t = new(T)
    t.a = 2
    t.b = 3
    assert t.a == 2
    assert t.b == 3

def test_null():
    T = Record({"a": Signed})
    n = null(T)
    n2 = null(T)
    assert n == n2

def test_identityhash():
    T = Record({"a": Signed, "b": Signed})
    t = new(T)
    t.a = 1
    t.b = 2
    t2 = new(T)
    t2.a = 1
    t2.b = 2
    assert identityhash(t) != identityhash(t2)       # xxx???
