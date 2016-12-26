"""
Buffer protocol support.
"""
from rpython.rlib import jit


class Buffer(object):
    """Abstract base class for buffers."""
    _immutable_ = True

    def getlength(self):
        """Returns the size in bytes (even if getitemsize() > 1)."""
        raise NotImplementedError

    def __len__(self):
        res = self.getlength()
        assert res >= 0
        return res

    def as_str(self):
        "Returns an interp-level string with the whole content of the buffer."
        # May be overridden.
        return self.getslice(0, self.getlength(), 1, self.getlength())

    def as_str_and_offset_maybe(self):
        """
        If the buffer is backed by a string, return a pair (string, offset), where
        offset is the offset inside the string where the buffer start.
        Else, return (None, 0).
        """
        return None, 0

    def getitem(self, index):
        "Returns the index'th character in the buffer."
        raise NotImplementedError   # Must be overriden.  No bounds checks.

    def __getitem__(self, i):
        return self.getitem(i)

    def getslice(self, start, stop, step, size):
        # May be overridden.  No bounds checks.
        return ''.join([self.getitem(i) for i in range(start, stop, step)])

    def __getslice__(self, start, stop):
        return self.getslice(start, stop, 1, stop - start)

    def setitem(self, index, char):
        "Write a character into the buffer."
        raise NotImplementedError   # Must be overriden.  No bounds checks.

    def __setitem__(self, i, char):
        return self.setitem(i, char)

    def setslice(self, start, string):
        # May be overridden.  No bounds checks.
        for i in range(len(string)):
            self.setitem(start + i, string[i])

    def get_raw_address(self):
        raise ValueError("no raw buffer")

    def getformat(self):
        return 'B'

    def getitemsize(self):
        return 1

    def getndim(self):
        return 1

    def getshape(self):
        return [self.getlength()]

    def getstrides(self):
        return [1]

    def releasebuffer(self):
        pass

class StringBuffer(Buffer):
    __slots__ = ['readonly', 'value']
    _immutable_ = True

    def __init__(self, value):
        self.value = value
        self.readonly = True

    def getlength(self):
        return len(self.value)

    def as_str(self):
        return self.value

    def as_str_and_offset_maybe(self):
        return self.value, 0

    def getitem(self, index):
        return self.value[index]

    def getslice(self, start, stop, step, size):
        if size == 0:
            return ""
        if step == 1:
            assert 0 <= start <= stop
            if start == 0 and stop == len(self.value):
                return self.value
            return self.value[start:stop]
        return Buffer.getslice(self, start, stop, step, size)


class SubBuffer(Buffer):
    __slots__ = ['buffer', 'offset', 'size', 'readonly']
    _immutable_ = True

    def __init__(self, buffer, offset, size):
        self.readonly = buffer.readonly
        if isinstance(buffer, SubBuffer):     # don't nest them
            # we want a view (offset, size) over a view
            # (buffer.offset, buffer.size) over buffer.buffer.
            # Note that either '.size' can be -1 to mean 'up to the end'.
            at_most = buffer.getlength() - offset
            if size > at_most or size < 0:
                if at_most < 0:
                    at_most = 0
                size = at_most
            offset += buffer.offset
            buffer = buffer.buffer
        #
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

    def as_str_and_offset_maybe(self):
        string, offset = self.buffer.as_str_and_offset_maybe()
        if string is not None:
            return string, offset+self.offset
        return None, 0

    def getitem(self, index):
        return self.buffer.getitem(self.offset + index)

    def getslice(self, start, stop, step, size):
        if start == stop:
            return ''     # otherwise, adding self.offset might make them
                          # out of bounds
        return self.buffer.getslice(self.offset + start, self.offset + stop,
                                    step, size)

    def setitem(self, index, char):
        self.buffer.setitem(self.offset + index, char)

    def setslice(self, start, string):
        if len(string) == 0:
            return        # otherwise, adding self.offset might make 'start'
                          # out of bounds
        self.buffer.setslice(self.offset + start, string)

    def get_raw_address(self):
        from rpython.rtyper.lltypesystem import rffi
        ptr = self.buffer.get_raw_address()
        return rffi.ptradd(ptr, self.offset)
