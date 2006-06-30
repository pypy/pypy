from pypy.rpython.ootypesystem.ootype import *

def test_type_comparison():
    T = Record({"a": Signed, "b": Signed})
    T2 = Record({"a": Signed, "b": Signed})
    T3 = Record({"a": Signed, "b": Unsigned})

    assert T == T2
    assert T2 != T3
    assert hash(T) == hash(T2)

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

def test_ooidentityhash():
    T = Record({"a": Signed, "b": Signed})
    t = new(T)
    t.a = 1
    t.b = 2
    t2 = new(T)
    t.a = 1
    t.b = 2
    assert ooidentityhash(t) != ooidentityhash(t2)

import py
def test_hash():
    py.test.skip("LowLevelType.__hash__ bug waiting to be fixed")
    T1 = Record({"item0": Signed, "item1": Signed})
    T2 = Record({"item0": Signed})

    hash(T2) # compute the hash, it will stored in __cached_hash
    T2._add_fields({"item1": Signed}) # modify the object
    assert T1 == T2
    assert hash(T1) == hash(T2)
