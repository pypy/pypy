# Deque Tests

# for passing the test on top of 2.3
from py.builtin import reversed
import pypy.lib.collections
pypy.lib.collections.reversed = reversed


n = 10
class Test_deque:
    def setup_method(self,method):
        
        from pypy.lib.collections import deque
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
        assert len(it) == n
        assert it.next() == 0
        assert len(it) == n-1
        self.d.pop()
        raises(RuntimeError,it.next)
        assert len(it) == 0
        assert list(it) == []
        
    def test_deque_reversed(self):
        it = reversed(self.d)
        assert len(it) == n
        assert it.next() == n-1
        assert len(it) == n-1
        assert it.next() == n-2
        assert len(it) == n-2
        self.d.pop()
        raises(RuntimeError,it.next)
        assert len(it) == 0
        assert list(it) == []

    
