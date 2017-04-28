"""
Buffer protocol support.
"""
from rpython.rlib.rgc import (
    nonmoving_raw_ptr_for_resizable_list, resizable_list_supporting_raw_ptr)
from rpython.rlib.signature import signature
from rpython.rlib import types

class Buffer(object):
    """Base class for buffers of bytes"""
    _attrs_ = ['readonly']
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
        If the buffer is backed by a string, return a pair (string, offset),
        where offset is the offset inside the string where the buffer start.
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

    @signature(types.any(), types.int(), types.int(), returns=types.str())
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

class ByteBuffer(Buffer):
    _immutable_ = True

    def __init__(self, n):
        self.data = resizable_list_supporting_raw_ptr(['\0'] * n)
        self.readonly = False

    def getlength(self):
        return len(self.data)

    def getitem(self, index):
        return self.data[index]

    def setitem(self, index, char):
        self.data[index] = char

    def get_raw_address(self):
        return nonmoving_raw_ptr_for_resizable_list(self.data)

class StringBuffer(Buffer):
    _attrs_ = ['readonly', 'value']
    _immutable_ = True

    def __init__(self, value):
        self.value = value
        self.readonly = 1

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

    def get_raw_address(self):
        from rpython.rtyper.lltypesystem import rffi
        # may still raise ValueError on some GCs
        return rffi.get_raw_address_of_string(self.value)

class SubBuffer(Buffer):
    _attrs_ = ['buffer', 'offset', 'size', 'readonly']
    _immutable_ = True

    @signature(types.any(), types.instance(Buffer), types.int(), types.int(),
               returns=types.none())
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
            return string, offset + self.offset
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
