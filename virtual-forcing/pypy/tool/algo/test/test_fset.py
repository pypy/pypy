from pypy.tool.algo.fset import FSet, checktree, emptyset
import random


def test_empty():
    assert FSet() is FSet([]) is emptyset
    assert len(emptyset) == 0
    assert list(emptyset) == []
    checktree(emptyset)

def test_iter():
    s = FSet(range(42))
    assert len(s) == 42
    assert list(s) == range(42)
    checktree(s)

def test_new():
    s = FSet(range(6, 42) + range(13))
    assert len(s) == 42
    assert list(s) == range(42)
    assert FSet(s) is s
    checktree(s)

def test_union():
    s1 = FSet([1, 10, 100, 1000])
    assert list(s1.union([])) == [1, 10, 100, 1000]
    assert list(s1.union([100])) == [1, 10, 100, 1000]
    assert list(s1.union([3, 4, 5])) == [1, 3, 4, 5, 10, 100, 1000]
    assert list(s1.union([1000, 1200, 1400])) == [1, 10, 100, 1000, 1200, 1400]
    assert list(s1.union(s1)) == [1, 10, 100, 1000]

def test_or():
    s1 = FSet([0, 3, 6])
    s2 = FSet([1, 3])
    assert list(s1 | s2) == [0, 1, 3, 6]

def test_eq():
    assert FSet([0, 3]) == FSet([0, 3])
    assert FSet([]) == emptyset
    assert FSet(range(42)) == FSet(range(42))
    assert FSet([]) != FSet([5])
    assert FSet(range(42)) != FSet(range(43))

def test_hash():
    assert hash(emptyset) != hash(FSet([1])) != hash(FSet([1, 2]))
    assert hash(FSet([1, 2])) == hash(FSet([1]) | FSet([2]))

def test_len():
    assert len(FSet([1, 2]) | FSet([2, 3])) == 3

def test_reasonable_speed(N=1000):
    d = emptyset
    for i in range(N):
        d |= FSet([i])
    checktree(d)
    assert list(d) == range(N)
    d = emptyset
    for i in range(N-1, -1, -1):
        d |= FSet([i])
    checktree(d)
    assert list(d) == range(N)
    d = emptyset
    lst = range(N)
    random.shuffle(lst)
    for i in lst:
        d |= FSet([i])
    checktree(d)
    assert list(d) == range(N)

def test_contains():
    assert 5 not in emptyset
    lst = range(0, 20, 2)
    random.shuffle(lst)
    d = FSet(lst)
    for x in range(20):
        assert (x in d) == (x in lst)
