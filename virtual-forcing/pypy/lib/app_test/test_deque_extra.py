# Deque Tests

# for passing the test on top of 2.3
from py.builtin import reversed
import pypy.lib.collections
pypy.lib.collections.reversed = reversed


n = 10
class Test_deque:
    def setup_method(self,method):
        
        from pypy.lib.collections import deque
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
        raises(TypeError, len, it)
        assert it.next() == 0
        self.d.pop()
        raises(RuntimeError, it.next)

    def test_deque_reversed(self):
        it = reversed(self.d)
        raises(TypeError, len, it)
        assert it.next() == n-1
        assert it.next() == n-2
        self.d.pop()
        raises(RuntimeError, it.next)

    def test_deque_remove(self):
        d = self.d
        raises(ValueError, d.remove, "foobar")

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
            raises(IndexError, d.remove, 'c')
            assert len(d) == 0
