# Naive collections implementation

class deque(list):
    def __init__(self, iter=None):
        # Do not run init on list, as it will empty list; deque test_basic does:
        #    d = deque(xrange(100))
        #    d.__init__(xrange(100, 200))
        if iter is not None:
            self.extend(iter)

    def appendleft(self, item):
        self.insert(0, item)

    def clear(self):
        del self[:]

    def extendleft(self, other):
        self[0:0] = [x for x in other][::-1]

    def popleft(self):
        x = self[0]
        del self[0]
        return x

    def rotate(self, step=1):
        if len(self) == 0:
            return
        step %= len(self)
        for i in range(step):
            self.appendleft(self.pop())

    def __repr__(self):
        return "%s(%s)" % (type(self).__name__, list.__repr__(self))

    def __reduce_ex__(self, proto):
        return type(self), (), self.__dict__, iter(self), None

    # We want to hide the fact that this deque is a subclass of list:
    # <type deque> should not be equal to <type list>
    def __eq__(self, other):
        return isinstance(other, deque) and list.__eq__(self, other)
    
    def __ne__(self, other):
        return not isinstance(other, deque) or list.__ne__(self, other)
    
    def __lt__(self, other):
        return isinstance(other, deque) and list.__lt__(self, other)
    
    def __le__(self, other):
        return isinstance(other, deque) and list.__le__(self, other)
    
    def __ge__(self, other):
        return isinstance(other, deque) and list.__ge__(self, other)
    
    def __gt__(self, other):
        return isinstance(other, deque) and list.__gt__(self, other)
