# Deque Tests
from __future__ import absolute_import
import py


n = 10
class Test_deque:
    def setup_method(self,method):
        
        from lib_pypy._collections import deque
        self.deque = deque
        self.d = deque(range(n))
        
    def test_deque(self):
        
        assert len(self.d) == n
        for i in range(n):
            assert i == self.d[i]
        for i in range(n-1, -1, -1):
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
        assert it.next() == n-1
        assert it.next() == n-2
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
            d = self.deque(['ab'])
            d.extend([MutateCmp(d, match), 'c'])
            py.test.raises(IndexError, d.remove, 'c')
            assert len(d) == 0
