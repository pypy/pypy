from pypy.tool.algo.unionref import UnionRef, UnionDict

def test_ref():
    x = object()
    ref = UnionRef(x)
    assert ref() is x
    assert ref == ref
    assert ref != UnionRef(x)

def test_merge():
    d1 = {1: '1'}
    d2 = {2: '2'}
    d3 = {3: '3'}
    d4 = {4: '4'}
    r1 = UnionRef(d1)
    r2 = UnionRef(d2)
    r3 = UnionRef(d3)
    r4 = UnionRef(d4)
    r1.merge(r1)
    assert r1 != r2 != r3 != r4
    r1.merge(r2)
    assert r1() is r2() == {1: '1', 2: '2'}
    assert r1 == r2
    r3.merge(r4)
    assert r3() is r4() == {3: '3', 4: '4'}
    assert r1 != r3
    assert r2 != r3
    assert r1 != r4
    assert r2 != r4
    r1.merge(r4)
    assert r1() is r2() is r3() is r4() == {1: '1', 2: '2', 3: '3', 4: '4'}
    assert r1 == r2 == r3 == r4

def test_uniondict():
    k1 = object()
    k2 = object()
    k3 = object()
    k4 = object()
    d = UnionDict()
    d[k1] = {1: '1'}
    d[k2] = {2: '2'}
    d[k3] = {3: '3'}
    d[k4] = {4: '4'}
    assert d[k1] == {1: '1'}
    assert d[k2] == {2: '2'}
    assert d[k3] == {3: '3'}
    assert d[k4] == {4: '4'}
    assert len(d) == 4
    d.merge(k1, k2)
    d.merge(k3, k4)
    assert d[k1] is d[k2] == {1: '1', 2: '2'}
    assert d[k3] is d[k4] == {3: '3', 4: '4'}
    d.merge(k1, k4)
    assert d[k1] is d[k2] is d[k3] is d[k4] == {1: '1', 2: '2', 3: '3', 4: '4'}
    assert len(d) == 4
