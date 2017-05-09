from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.lltypesystem.rstr import STR
from rpython.rtyper.annlowlevel import llstr, hlstr
from rpython.rlib.buffer import Buffer

class MutableStringBuffer(Buffer):
    """
    A writeable buffer to incrementally fill a string of a fixed size.

    You can fill the string by calling setitem, setslice and typed_write, and
    get the result by calling finish().

    After you call finish(), you can no longer modify the buffer. There is no
    check, you will probably get a segfault after translation.

    You can call finish() only once.
    """
    _attrs_ = ['readonly', 'll_val']
    _immutable_ = True

    def __init__(self, size):
        self.readonly = False
        # rstr.mallocstr does not pass zero=True, so we call lltype.malloc
        # directly
        self.ll_val = lltype.malloc(STR, size, zero=True)

    def finish(self):
        if not self.ll_val:
            raise ValueError("Cannot call finish() twice")
        result = hlstr(self.ll_val)
        self.ll_val = lltype.nullptr(STR)
        self.readonly = True
        return result

    def as_str(self):
        raise ValueError('as_str() is not supported. Use finish() instead')

    def setitem(self, index, char):
        self.ll_val.chars[index] = char
