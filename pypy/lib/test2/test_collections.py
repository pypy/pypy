from pypy.lib import collections
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
    
class SubclassWithKwargs(collections.deque):
    def __init__(self, newarg=1):
        collections.deque.__init__(self)

def test_subclass_with_kwargs():
    # SF bug #1486663 -- this used to erroneously raise a TypeError
    SubclassWithKwargs(newarg=1)
