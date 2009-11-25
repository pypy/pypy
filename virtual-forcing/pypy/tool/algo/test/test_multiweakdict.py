import py, gc
from pypy.tool.algo.multiweakdict import MultiWeakKeyDictionary


class A(object):
    pass


def test_simple():
    d = MultiWeakKeyDictionary()
    a1 = A()
    a2 = A()
    a3 = A()
    d[a1, a2] = 12
    d[a1,] = 1
    d[a2,] = 2
    d[a2, a1] = 21
    d[a2, a2] = 22
    d[()] = 0
    assert d[a1, a2] == 12
    assert d[a1,] == 1
    assert d[a2,] == 2
    assert d[a2, a1] == 21
    assert d[a2, a2] == 22
    assert d[()] == 0
    assert dict.fromkeys(d.keys()) == {(a1, a2): None,
                                       (a1,): None,
                                       (a2,): None,
                                       (a2, a1): None,
                                       (a2, a2): None,
                                       (): None}
    del d[a2,]
    assert dict.fromkeys(d.keys()) == {(a1, a2): None,
                                       (a1,): None,
                                       (a2, a1): None,
                                       (a2, a2): None,
                                       (): None}
    assert d[a1, a2] == 12
    assert d[a1,] == 1
    assert d[a2, a1] == 21
    assert d[a2, a2] == 22
    assert d[()] == 0
    py.test.raises(KeyError, "d[a2,]")

    del a1
    locals()   # obscure fix for CPython -- make sure a1 is no longer in
               # the cached f_locals of the frame
    gc.collect()   # less obscure fix for other Python implementations
    assert dict.fromkeys(d.keys()) == {(a2, a2): None,
                                       (): None}
    assert d[a2, a2] == 22
    assert d[()] == 0
