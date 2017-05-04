"""
Buffer protocol support.
"""
from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.lltypesystem.rstr import STR
from rpython.rtyper.annlowlevel import llstr
from rpython.rlib.objectmodel import specialize
from rpython.rlib import jit
from rpython.rlib.rgc import (resizable_list_supporting_raw_ptr,
        nonmoving_raw_ptr_for_resizable_list)


class CannotRead(Exception):
    """
    Exception raised by Buffer.typed_read in case it is not possible to
    accomplish the request. This might be because it is not supported by the
    specific type of buffer, or because of alignment issues.
    """

class Buffer(object):
    """Abstract base class for buffers."""
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

    @specialize.ll_and_arg(1)
    def typed_read(self, TP, byte_offset):
        raise CannotRead



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

    @specialize.ll_and_arg(1)
    def typed_read(self, TP, byte_offset):
        # WARNING: the 'byte_offset' is, as its name says, measured in bytes;
        # however, it should be aligned for TP, otherwise on some platforms this
        # code will crash!
        lls = llstr(self.value)
        base_ofs = (llmemory.offsetof(STR, 'chars') +
                    llmemory.itemoffsetof(STR.chars, 0))
        scale_factor = llmemory.sizeof(lltype.Char)
        return llop.gc_load_indexed(TP, lls, byte_offset,
                                    scale_factor, base_ofs)


class SubBuffer(Buffer):
    _attrs_ = ['buffer', 'offset', 'size', 'readonly']
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

    @specialize.ll_and_arg(1)
    def typed_read(self, TP, byte_offset):
        return self.buffer.typed_read(TP, byte_offset + self.offset)
