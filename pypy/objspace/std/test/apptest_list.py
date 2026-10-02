# coding: iso-8859-15

import pytest

def test_is_true():
    assert not bool([])
    assert bool([5])
    assert bool([5, 3])

def test_len():
    assert len([]) == 0
    assert len([5]) == 1
    assert len([5, 3, 99] * 111) == 333
    assert len([u'\u2039']) == 1

def test_getitem():
    l = [5, 3]
    assert l[0] == 5
    assert l[1] == 3
    assert l[-2] == 5
    assert l[-1] == 3
    with raises(IndexError):
        l[2]
    with raises(IndexError):
        l[42]
    with raises(IndexError):
        l[-3]

def test_iter():
    it = iter([5, 3, 99])
    assert next(it) == 5
    assert next(it) == 3
    assert next(it) == 99
    with raises(StopIteration):
        next(it)
    with raises(StopIteration):
        next(it)

def test_contains():
    l = [5, 3, 99]
    assert 5 in l
    assert 99 in l
    assert 11 not in l
    assert l not in l

def test_add():
    l0 = []
    l1 = [5, 3, 99]
    l2 = [-7] * 111
    assert l1 + l1 == [5, 3, 99, 5, 3, 99]
    assert l1 + l2 == [5, 3, 99] + [-7] * 111
    assert l1 + l0 == l1
    assert l0 + l2 == l2

def test_mul():
    assert [2] * 3 == [2, 2, 2]
    # commute
    assert 3 * [2] == [2, 2, 2]

def test_setitem():
    l = [5, 3]
    l[1] = 7
    assert l == [5, 7]
    l[-2] = 8
    assert l == [8, 7]
    with raises(IndexError):
        l[2] = 5
    with raises(IndexError):
        l[-3] = 5

def test_eq():
    l0 = []
    l1 = [5, 3, 99]
    l2 = [5, 3, 99]
    l3 = [5, 3, 99, -1]

    assert not l0 == l1
    assert not l1 == l0
    assert l1 == l1
    assert l1 == l2
    assert not l2 == l3

def test_ne():
    l0 = []
    l1 = [5, 3, 99]
    l2 = [5, 3, 99]
    l3 = [5, 3, 99, -1]

    assert l0 != l1
    assert l1 != l0
    assert not l1 != l1
    assert not l1 != l2
    assert l2 != l3

def test_lt():
    l0 = []
    l1 = [5, 3, 99]
    l2 = [5, 3, 99]
    l3 = [5, 3, 99, -1]
    l4 = [5, 3, 9, -1]

    assert l0 < l1
    assert not l1 < l0
    assert not l1 < l1
    assert not l1 < l2
    assert l2 < l3
    assert l4 < l3

def test_ge():
    l0 = []
    l1 = [5, 3, 99]
    l2 = [5, 3, 99]
    l3 = [5, 3, 99, -1]
    l4 = [5, 3, 9, -1]

    assert not l0 >= l1
    assert l1 >= l0
    assert l1 >= l1
    assert l1 >= l2
    assert not l2 >= l3
    assert not l4 >= l3

def test_gt():
    l0 = []
    l1 = [5, 3, 99]
    l2 = [5, 3, 99]
    l3 = [5, 3, 99, -1]
    l4 = [5, 3, 9, -1]

    assert not l0 > l1
    assert l1 > l0
    assert not l1 > l1
    assert not l1 > l2
    assert not l2 > l3
    assert not l4 > l3

def test_reversed_subclass_overriding_len():
    # list.__reversed__ uses the real length, not a __len__ override
    class L(list):
        def __len__(self):
            return 10

    assert list(reversed(L([1, 2, 3]))) == [3, 2, 1]
    assert list(reversed(L([]))) == []

def test_le():
    l0 = []
    l1 = [5, 3, 99]
    l2 = [5, 3, 99]
    l3 = [5, 3, 99, -1]
    l4 = [5, 3, 9, -1]

    assert l0 <= l1
    assert not l1 <= l0
    assert l1 <= l1
    assert l1 <= l2
    assert l2 <= l3
    assert l4 <= l3
