from __future__ import absolute_import
from lib_pypy import _collections as collections
import py

class TestDeque:
    def test_remove_empty(self):
        d = collections.deque([])
        py.test.raises(ValueError, d.remove, 1)

    def test_remove_mutating(self):
        class MutatingCmp(object):
            def __eq__(self, other):
                d.clear()
                return True

        d = collections.deque([MutatingCmp()])
        py.test.raises(IndexError, d.remove, 1)

    def test_maxlen(self):
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

    def test_count(self):
        d = collections.deque([1, 2, 2, 3, 2])
        assert d.count(2) == 3
        assert d.count(4) == 0

    def test_reverse(self):
        d = collections.deque([1, 2, 2, 3, 2])
        d.reverse()
        assert list(d) == [2, 3, 2, 2, 1]

        d = collections.deque(range(100))
        d.reverse()
        assert list(d) == range(99, -1, -1)

    def test_subclass_with_kwargs(self):
        class SubclassWithKwargs(collections.deque):
            def __init__(self, newarg=1):
                collections.deque.__init__(self)

        # SF bug #1486663 -- this used to erroneously raise a TypeError
        SubclassWithKwargs(newarg=1)
