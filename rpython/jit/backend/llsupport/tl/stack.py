from rpython.rlib.jit import JitDriver, hint, dont_look_inside, promote

class Stack(object):
    _virtualizable_ = ['stackpos', 'stack[*]']

    @staticmethod
    def from_items(space, elems):
        s = Stack(len(elems))
        for elem in elems:
            if isinstance(elem, list):
                elem = [space.wrap(e) for e in elem]
            s.append(space.wrap(elem))
        return s


    def __init__(self, size):
        self = hint(self, access_directly=True, fresh_virtualizable=True)
        self.stack = [None] * size
        self.stackpos = 0        # always store a known-nonneg integer here

    def size(self):
        return self.stackpos

    def copy(self, values=False):
        """ NOT_RPYTHON """
        copy = Stack(self.size())
        for item in self.stack:
            if values:
                copy.append(item.copy())
            else:
                copy.append(item)
        return copy

    def append(self, elem):
        while len(self.stack) <= self.stackpos:
            self.stack.append(None)
        self.stack[self.stackpos] = elem
        self.stackpos += 1

    def peek(self, i):
        stackpos = self.stackpos - i - 1
        if stackpos < 0:
            raise IndexError
        return self.stack[stackpos]

    def pop(self):
        stackpos = self.stackpos - 1
        if stackpos < 0:
            raise IndexError
        self.stackpos = stackpos     # always store a known-nonneg integer here
        elem = self.stack[stackpos]
        self.stack[stackpos] = None
        return elem

    def pick(self, i):
        n = self.stackpos - i - 1
        assert n >= 0
        self.append(self.stack[n])

    def put(self, i):
        elem = self.pop()
        n = self.stackpos - i - 1
        assert n >= 0
        self.stack[n] = elem

    @dont_look_inside
    def roll(self, r):
        if r < -1:
            i = self.stackpos + r
            if i < 0:
                raise IndexError
            n = self.stackpos - 1
            assert n >= 0
            elem = self.stack[n]
            for j in range(self.stackpos - 2, i - 1, -1):
                assert j >= 0
                self.stack[j + 1] = self.stack[j]
            self.stack[i] = elem
        elif r > 1:
            i = self.stackpos - r
            if i < 0:
                raise IndexError
            elem = self.stack[i]
            for j in range(i, self.stackpos - 1):
                self.stack[j] = self.stack[j + 1]
            n = self.stackpos - 1
            assert n >= 0
            self.stack[n] = elem

    def reset(self):
        self.stack = [None] * self.size()
        self.stackpos = 0

    def __repr__(self):
        """ NOT_RPYTHON """
        entry_types = [e.TYPE for e in self.stack[:self.stackpos]]
        return "Stack(%s)" % ','.join(entry_types)

