from __future__ import absolute_import
from .. import _collections as collections
import py

def test_deque_remove_empty():
    d = collections.deque([])
    py.test.raises(ValueError, d.remove, 1)

def test_deque_remove_mutating():
    class MutatingCmp(object):
        def __eq__(self, other):
            d.clear()
            return True

    d = collections.deque([MutatingCmp()])
    py.test.raises(IndexError, d.remove, 1)

def test_deque_maxlen():
    d = collections.deque([], 3)
    d.append(1); d.append(2); d.append(3); d.append(4)
    assert list(d) == [2, 3, 4]
    assert repr(d) == "deque([2, 3, 4], maxlen=3)"

    import pickle
    d2 = pickle.loads(pickle.dumps(d))
    assert repr(d2) == "deque([2, 3, 4], maxlen=3)"

    import copy
    d3 = copy.copy(d)
    assert repr(d3) == "deque([2, 3, 4], maxlen=3)"

def test_deque_count():
    d = collections.deque([1, 2, 2, 3, 2])
    assert d.count(2) == 3
    assert d.count(4) == 0

class SubclassWithKwargs(collections.deque):
    def __init__(self, newarg=1):
        collections.deque.__init__(self)

def test_subclass_with_kwargs():
    # SF bug #1486663 -- this used to erroneously raise a TypeError
    SubclassWithKwargs(newarg=1)
