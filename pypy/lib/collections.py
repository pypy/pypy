"""High performance data structures
"""
#
# Copied and completed from the sandbox of CPython
#   (nondist/sandbox/collections/pydeque.py rev 1.1, Raymond Hettinger)
#

import operator
try:
    from thread import get_ident as _thread_ident
except ImportError:
    def _thread_ident():
        return -1


n = 30
LFTLNK = n
RGTLNK = n+1
BLOCKSIZ = n+2

class deque(object):

    def __new__(cls, iterable=(), *args, **kw):
        self = super(deque, cls).__new__(cls, *args, **kw)
        self.clear()
        return self

    def __init__(self, iterable=()):
        add = self.append
        for elem in iterable:
            add(elem)

    def clear(self):
        self.right = self.left = [None] * BLOCKSIZ
        self.rightndx = n//2   # points to last written element
        self.leftndx = n//2+1
        self.length = 0
        self.state = 0

    def append(self, x):
        self.state += 1
        self.rightndx += 1
        if self.rightndx == n:
            newblock = [None] * BLOCKSIZ
            self.right[RGTLNK] = newblock
            newblock[LFTLNK] = self.right
            self.right = newblock
            self.rightndx = 0
        self.length += 1
        self.right[self.rightndx] = x

    def appendleft(self, x):
        self.state += 1
        self.leftndx -= 1
        if self.leftndx == -1:
            newblock = [None] * BLOCKSIZ
            self.left[LFTLNK] = newblock
            newblock[RGTLNK] = self.left
            self.left = newblock
            self.leftndx = n-1
        self.length += 1
        self.left[self.leftndx] = x

    def extend(self, iterable):
        for elem in iterable:
            self.append(elem)

    def extendleft(self, iterable):
        for elem in iterable:
            self.appendleft(elem)

    def pop(self):
        if self.left is self.right and self.leftndx > self.rightndx:
            raise IndexError, "pop from an empty deque"
        x = self.right[self.rightndx]
        self.right[self.rightndx] = None
        self.length -= 1
        self.rightndx -= 1
        self.state += 1
        if self.rightndx == -1:
            prevblock = self.right[LFTLNK]
            if prevblock is None:
                # the deque has become empty; recenter instead of freeing block
                self.rightndx = n//2
                self.leftndx = n//2+1
            else:
                prevblock[RGTLNK] = None
                self.right[LFTLNK] = None
                self.right = prevblock
                self.rightndx = n-1
        return x

    def popleft(self):
        if self.left is self.right and self.leftndx > self.rightndx:
            raise IndexError, "pop from an empty deque"
        x = self.left[self.leftndx]
        self.left[self.leftndx] = None
        self.length -= 1
        self.leftndx += 1
        self.state += 1
        if self.leftndx == n:
            prevblock = self.left[RGTLNK]
            if prevblock is None:
                # the deque has become empty; recenter instead of freeing block
                self.rightndx = n//2
                self.leftndx = n//2+1
            else:
                prevblock[LFTLNK] = None
                self.left[RGTLNK] = None
                self.left = prevblock
                self.leftndx = 0
        return x

    def remove(self, value):
        # Need to be defensive for mutating comparisons
        for i in range(len(self)):
            if self[i] == value:
                del self[i]
                return
        raise ValueError("deque.remove(x): x not in deque")

    def rotate(self, n=1):
        length = len(self)
        if length == 0:
            return
        halflen = (length+1) >> 1
        if n > halflen or n < -halflen:
            n %= length
            if n > halflen:
                n -= length
            elif n < -halflen:
                n += length
        while n > 0:
            self.appendleft(self.pop())
            n -= 1
        while n < 0:
            self.append(self.popleft())
            n += 1

    def __repr__(self):
        threadlocalattr = '__repr' + str(_thread_ident())
        if threadlocalattr in self.__dict__:
            return 'deque([...])'
        else:
            self.__dict__[threadlocalattr] = True
            try:
                return 'deque(%r)' % (list(self),)
            finally:
                del self.__dict__[threadlocalattr]

    def __iter__(self):
        return deque_iterator(self, self._iter_impl)

    def _iter_impl(self, original_state, giveup):
        if self.state != original_state:
            giveup()
        block = self.left
        while block:
            l, r = 0, n
            if block is self.left:
                l = self.leftndx
            if block is self.right:
                r = self.rightndx + 1
            for elem in block[l:r]:
                yield elem
                if self.state != original_state:
                    giveup()
            block = block[RGTLNK]

    def __reversed__(self):
        return deque_iterator(self, self._reversed_impl)

    def _reversed_impl(self, original_state, giveup):
        if self.state != original_state:
            giveup()
        block = self.right
        while block:
            l, r = 0, n
            if block is self.left:
                l = self.leftndx
            if block is self.right:
                r = self.rightndx + 1
            for elem in reversed(block[l:r]):
                yield elem
                if self.state != original_state:
                    giveup()
            block = block[LFTLNK]

    def __len__(self):
        #sum = 0
        #block = self.left
        #while block:
        #    sum += n
        #    block = block[RGTLNK]
        #return sum + self.rightndx - self.leftndx + 1 - n
        return self.length

    def __getref(self, index):
        if index >= 0:
            block = self.left
            while block:
                l, r = 0, n
                if block is self.left:
                    l = self.leftndx
                if block is self.right:
                    r = self.rightndx + 1
                span = r-l
                if index < span:
                    return block, l+index
                index -= span
                block = block[RGTLNK]
        else:
            block = self.right
            while block:
                l, r = 0, n
                if block is self.left:
                    l = self.leftndx
                if block is self.right:
                    r = self.rightndx + 1
                negative_span = l-r
                if index >= negative_span:
                    return block, r+index
                index -= negative_span
                block = block[LFTLNK]
        raise IndexError("deque index out of range")

    def __getitem__(self, index):
        block, index = self.__getref(index)
        return block[index]

    def __setitem__(self, index, value):
        block, index = self.__getref(index)
        block[index] = value

    def __delitem__(self, index):
        length = len(self)
        if index >= 0:
            if index >= length:
                raise IndexError("deque index out of range")
            self.rotate(-index)
            self.popleft()
            self.rotate(index)
        else:
            index = ~index
            if index >= length:
                raise IndexError("deque index out of range")
            self.rotate(index)
            self.pop()
            self.rotate(-index)

    def __reduce_ex__(self, proto):
        return type(self), (), self.__dict__, iter(self), None

    def __hash__(self):
        raise TypeError, "deque objects are unhashable"

    def __copy__(self):
        return self.__class__(self)

    # XXX make comparison more efficient
    def __eq__(self, other):
        if isinstance(other, deque):
            return list(self) == list(other)
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, deque):
            return list(self) != list(other)
        else:
            return NotImplemented

    def __lt__(self, other):
        if isinstance(other, deque):
            return list(self) < list(other)
        else:
            return NotImplemented

    def __le__(self, other):
        if isinstance(other, deque):
            return list(self) <= list(other)
        else:
            return NotImplemented

    def __gt__(self, other):
        if isinstance(other, deque):
            return list(self) > list(other)
        else:
            return NotImplemented

    def __ge__(self, other):
        if isinstance(other, deque):
            return list(self) >= list(other)
        else:
            return NotImplemented

class deque_iterator(object):

    def __init__(self, deq, itergen):
        self.counter = len(deq)
        def giveup():
            self.counter = 0
            raise RuntimeError, "deque mutated during iteration"
        self._gen = itergen(deq.state, giveup)

    def next(self):
        res =  self._gen.next()
        self.counter -= 1
        return res

    def __iter__(self):
        return self

class defaultdict(dict):
    
    def __init__(self, *args, **kwds):
        self.default_factory = None
        if 'default_factory' in kwds:
            self.default_factory = kwds.pop('default_factory')
        elif len(args) > 0 and callable(args[0]):
            self.default_factory = args[0]
            args = args[1:]
        super(defaultdict, self).__init__(*args, **kwds)
 
    def __missing__(self, key):
        # from defaultdict docs
        if self.default_factory is None: 
            raise KeyError(key)
        self[key] = value = self.default_factory()
        return value

    def __repr__(self, recurse=set()):
        if id(self) in recurse:
            return "defaultdict(...)"
        try:
            recurse.add(id(self))
            return "defaultdict(%s, %s)" % (repr(self.default_factory), super(defaultdict, self).__repr__())
        finally:
            recurse.remove(id(self))

    def copy(self):
        return type(self)(self, default_factory=self.default_factory)
    
    def __copy__(self):
        return self.copy()

    def __reduce__(self):
        """
        __reduce__ must return a 5-tuple as follows:

           - factory function
           - tuple of args for the factory function
           - additional state (here None)
           - sequence iterator (here None)
           - dictionary iterator (yielding successive (key, value) pairs

           This API is used by pickle.py and copy.py.
        """
        return (type(self), (self.default_factory,), None, None, self.iteritems())

