"""
Buffer protocol support.
"""
from pypy.interpreter.error import OperationError
from rpython.rlib.objectmodel import import_from_mixin


class Buffer(object):
    """Abstract base class for buffers."""
    __slots__ = []

    def getlength(self):
        raise NotImplementedError

    def as_str(self):
        "Returns an interp-level string with the whole content of the buffer."
        # May be overridden.
        return self.getslice(0, self.getlength(), 1, self.getlength())

    def getitem(self, index):
        "Returns the index'th character in the buffer."
        raise NotImplementedError   # Must be overriden.  No bounds checks.

    def getslice(self, start, stop, step, size):
        # May be overridden.  No bounds checks.
        return ''.join([self.getitem(i) for i in range(start, stop, step)])

    def get_raw_address(self):
        raise ValueError("no raw buffer")

    def is_writable(self):
        return False


class RWBuffer(Buffer):
    """Abstract base class for read-write buffers."""
    __slots__ = []

    def is_writable(self):
        return True

    def setitem(self, index, char):
        "Write a character into the buffer."
        raise NotImplementedError   # Must be overriden.  No bounds checks.

    def setslice(self, start, string):
        # May be overridden.  No bounds checks.
        for i in range(len(string)):
            self.setitem(start + i, string[i])


class StringBuffer(Buffer):
    __slots__ = ['value']

    def __init__(self, value):
        self.value = value

    def getlength(self):
        return len(self.value)

    def as_str(self):
        return self.value

    def getitem(self, index):
        return self.value[index]

    def getslice(self, start, stop, step, size):
        if size == 0:
            return ""
        if step == 1:
            assert 0 <= start <= stop
            return self.value[start:stop]
        return "".join([self.value[start + i*step] for i in xrange(size)])
# ____________________________________________________________


class SubBufferMixin(object):
    _attrs_ = ['buffer', 'offset', 'size']

    def __init__(self, buffer, offset, size):
        self.buffer = buffer
        self.offset = offset
        self.size = size

    def getlength(self):
        at_most = self.buffer.getlength() - self.offset
        if 0 <= self.size <= at_most:
            return self.size
        elif at_most >= 0:
            return at_most
        else:
            return 0

    def getitem(self, index):
        return self.buffer.getitem(self.offset + index)

    def getslice(self, start, stop, step, size):
        if start == stop:
            return ''     # otherwise, adding self.offset might make them
                          # out of bounds
        return self.buffer.getslice(self.offset + start, self.offset + stop,
                                    step, size)


class SubBuffer(Buffer):
    import_from_mixin(SubBufferMixin)


class RWSubBuffer(RWBuffer):
    import_from_mixin(SubBufferMixin)

    def setitem(self, index, char):
        self.buffer.setitem(self.offset + index, char)

    def setslice(self, start, string):
        if len(string) == 0:
            return        # otherwise, adding self.offset might make 'start'
                          # out of bounds
        self.buffer.setslice(self.offset + start, string)
