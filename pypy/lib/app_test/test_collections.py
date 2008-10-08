import py
import collections

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
    
