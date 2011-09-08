"""
Miscellaneous utilities.
"""

import types

from pypy.rlib.rarithmetic import r_uint

class RootStack:
    pass

class Stack(RootStack):
    """Utility class implementing a stack."""

    _annspecialcase_ = "specialize:ctr_location" # polymorphic

    def __init__(self):
        self.items = []

    def clone(self):
        s = self.__class__()
        for item in self.items:
            try:
                item = item.clone()
            except AttributeError:
                pass
            s.push(item)
        return s

    def push(self, item):
        self.items.append(item)

    def pop(self):
        return self.items.pop()

    def drop(self, n):
        if n > 0:
            del self.items[-n:]

    def top(self, position=0):
        """'position' is 0 for the top of the stack, 1 for the item below,
        and so on.  It must not be negative."""
        if position < 0:
            raise ValueError, 'negative stack position'
        if position >= len(self.items):
            raise IndexError, 'not enough entries in stack'
        return self.items[~position]

    def set_top(self, value, position=0):
        """'position' is 0 for the top of the stack, 1 for the item below,
        and so on.  It must not be negative."""
        if position < 0:
            raise ValueError, 'negative stack position'
        if position >= len(self.items):
            raise IndexError, 'not enough entries in stack'
        self.items[~position] = value

    def depth(self):
        return len(self.items)

    def empty(self):
        return len(self.items) == 0


class FixedStack(RootStack):
    _annspecialcase_ = "specialize:ctr_location" # polymorphic

    # unfortunately, we have to re-do everything
    def __init__(self):
        pass

    def setup(self, stacksize):
        self.ptr = r_uint(0) # we point after the last element
        self.items = [None] * stacksize

    def clone(self):
        # this is only needed if we support flow space
        s = self.__class__()
        s.setup(len(self.items))
        for item in self.items[:self.ptr]:
            try:
                item = item.clone()
            except AttributeError:
                pass
            s.push(item)
        return s

    def push(self, item):
        ptr = self.ptr
        self.items[ptr] = item
        self.ptr = ptr + 1

    def pop(self):
        ptr = self.ptr - 1
        ret = self.items[ptr]   # you get OverflowError if the stack is empty
        self.items[ptr] = None
        self.ptr = ptr
        return ret

    def drop(self, n):
        while n > 0:
            n -= 1
            self.ptr -= 1
            self.items[self.ptr] = None

    def top(self, position=0):
        # for a fixed stack, we assume correct indices
        return self.items[self.ptr + ~position]

    def set_top(self, value, position=0):
        # for a fixed stack, we assume correct indices
        self.items[self.ptr + ~position] = value

    def depth(self):
        return self.ptr

    def empty(self):
        return not self.ptr


class InitializedClass(type):
    """NOT_RPYTHON.  A meta-class that allows a class to initialize itself (or
    its subclasses) by calling __initclass__() as a class method."""
    def __init__(self, name, bases, dict):
        super(InitializedClass, self).__init__(name, bases, dict)
        for basecls in self.__mro__:
            raw = basecls.__dict__.get('__initclass__')
            if isinstance(raw, types.FunctionType):
                raw(self)   # call it as a class method


class RwDictProxy(object):
    """NOT_RPYTHON.  A dict-like class standing for 'cls.__dict__', to work
    around the fact that the latter is a read-only proxy for new-style
    classes."""
    
    def __init__(self, cls):
        self.cls = cls

    def __getitem__(self, attr):
        return self.cls.__dict__[attr]

    def __setitem__(self, attr, value):
        setattr(self.cls, attr, value)

    def __contains__(self, value):
        return value in self.cls.__dict__

    def items(self):
        return self.cls.__dict__.items()


class ThreadLocals:
    """Pseudo thread-local storage, for 'space.threadlocals'.
    This is not really thread-local at all; the intention is that the PyPy
    implementation of the 'thread' module knows how to provide a real
    implementation for this feature, and patches 'space.threadlocals' when
    'thread' is initialized.
    """
    _value = None

    def getvalue(self):
        return self._value

    def setvalue(self, value):
        self._value = value

    def getmainthreadvalue(self):
        return self._value

    def getallvalues(self):
        return {0: self._value}

