"""
Miscellaneous utilities.
"""

import types


class Stack:
    """Utility class implementing a stack."""

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

    def top(self, position=0):
        """'position' is 0 for the top of the stack, 1 for the item below,
        and so on.  It must not be negative."""
        return self.items[~position]

    def depth(self):
        return len(self.items)

    def empty(self):
        return not self.items


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
    """Thread-local storage."""

    def __init__(self):
        self.executioncontext = None

# XXX no thread support yet, so this is easy :-)
_locals = ThreadLocals()
def getthreadlocals():
    return _locals
