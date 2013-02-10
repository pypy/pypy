"""
Extra tests for the pure Python PyPy _collections module
(not used in normal PyPy's)
"""

from __future__ import absolute_import
from lib_pypy import _collections as collections
import py

class TestDeque:
    def setup_method(self, method):
        self.n = 10
        self.d = collections.deque(range(self.n))

    def test_deque(self):
        assert len(self.d) == self.n
        for i in range(self.n):
            assert i == self.d[i]
        for i in range(self.n-1, -1, -1):
            assert self.d.pop() == i
        assert len(self.d) == 0

    def test_deque_iter(self):
        it = iter(self.d)
        py.test.raises(TypeError, len, it)
        assert it.next() == 0
        self.d.pop()
        py.test.raises(RuntimeError, it.next)

    def test_deque_reversed(self):
        it = reversed(self.d)
        py.test.raises(TypeError, len, it)
        assert it.next() == self.n-1
        assert it.next() == self.n-2
        self.d.pop()
        py.test.raises(RuntimeError, it.next)

    def test_deque_remove(self):
        d = self.d
        py.test.raises(ValueError, d.remove, "foobar")

    def test_mutate_during_remove(self):
        # Handle evil mutator
        class MutateCmp:
            def __init__(self, deque, result):
                self.deque = deque
                self.result = result
            def __eq__(self, other):
                self.deque.clear()
                return self.result

        for match in (True, False):
            d = collections.deque(['ab'])
            d.extend([MutateCmp(d, match), 'c'])
            py.test.raises(IndexError, d.remove, 'c')
            assert len(d) == 0

class TestDequeExtra:
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

    def test_remove_failing(self):
        class FailingCmp(object):
            def __eq__(self, other):
                assert False

        f = FailingCmp()
        d = collections.deque([1, 2, 3, f, 4, 5])
        d.remove(3)
        py.test.raises(AssertionError, d.remove, 4)
        assert d == collections.deque([1, 2, f, 4, 5])

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

class TestDefaultDict:
    def test_copy(self):
        def f():
            return 42
        d = collections.defaultdict(f, {2: 3})
        #
        d1 = d.copy()
        assert type(d1) is collections.defaultdict
        assert len(d1) == 1
        assert d1[2] == 3
        assert d1[3] == 42
        #
        import copy
        d2 = copy.deepcopy(d)
        assert type(d2) is collections.defaultdict
        assert len(d2) == 1
        assert d2[2] == 3
        assert d2[3] == 42
