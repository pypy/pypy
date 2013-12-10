from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.buffer import RWBuffer
from pypy.interpreter.error import operationerrfmt
from pypy.interpreter.gateway import unwrap_spec, interp2app
from pypy.interpreter.typedef import TypeDef, make_weakref_descr
from pypy.module._cffi_backend import cdataobj, ctypeptr, ctypearray

from rpython.rtyper.lltypesystem import rffi


class LLBuffer(RWBuffer):
    _immutable_ = True

    def __init__(self, raw_cdata, size):
        self.raw_cdata = raw_cdata
        self.size = size

    def getlength(self):
        return self.size

    def getitem(self, index):
        return self.raw_cdata[index]

    def setitem(self, index, char):
        self.raw_cdata[index] = char

    def get_raw_address(self):
        return self.raw_cdata

    def getslice(self, start, stop, step, size):
        if step == 1:
            return rffi.charpsize2str(rffi.ptradd(self.raw_cdata, start), size)
        return RWBuffer.getslice(self, start, stop, step, size)

    def setslice(self, start, string):
        raw_cdata = rffi.ptradd(self.raw_cdata, start)
        for i in range(len(string)):
            raw_cdata[i] = string[i]


class MiniBuffer(W_Root):
    # a different subclass of W_Root for the MiniBuffer, because we
    # want a slightly different (simplified) API at the level of Python.

    def __init__(self, buffer, keepalive=None):
        self.buffer = buffer
        self.keepalive = keepalive

    def descr_len(self, space):
        return self.buffer.descr_len(space)

    def descr_getitem(self, space, w_index):
        return self.buffer.descr_getitem(space, w_index)

    @unwrap_spec(newstring='bufferstr')
    def descr_setitem(self, space, w_index, newstring):
        self.buffer.descr_setitem(space, w_index, newstring)

    def descr__buffer__(self, space):
        return self.buffer.descr__buffer__(space)

    def descr_str(self, space):
        return space.wrap(self.buffer.as_str())


MiniBuffer.typedef = TypeDef(
    "buffer",
    __module__ = "_cffi_backend",
    __len__ = interp2app(MiniBuffer.descr_len),
    __getitem__ = interp2app(MiniBuffer.descr_getitem),
    __setitem__ = interp2app(MiniBuffer.descr_setitem),
    __buffer__ = interp2app(MiniBuffer.descr__buffer__),
    __weakref__ = make_weakref_descr(MiniBuffer),
    __str__ = interp2app(MiniBuffer.descr_str),
    )
MiniBuffer.typedef.acceptable_as_base_class = False


@unwrap_spec(w_cdata=cdataobj.W_CData, size=int)
def buffer(space, w_cdata, size=-1):
    ctype = w_cdata.ctype
    if isinstance(ctype, ctypeptr.W_CTypePointer):
        if size < 0:
            size = ctype.ctitem.size
    elif isinstance(ctype, ctypearray.W_CTypeArray):
        if size < 0:
            size = w_cdata._sizeof()
    else:
        raise operationerrfmt(space.w_TypeError,
                              "expected a pointer or array cdata, got '%s'",
                              ctype.name)
    if size < 0:
        raise operationerrfmt(space.w_TypeError,
                              "don't know the size pointed to by '%s'",
                              ctype.name)
    return space.wrap(MiniBuffer(LLBuffer(w_cdata._cdata, size), w_cdata))
