from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import oefmt
from pypy.interpreter.gateway import unwrap_spec, interp2app
from pypy.interpreter.typedef import TypeDef, make_weakref_descr
from pypy.module._cffi_backend import cdataobj, ctypeptr, ctypearray
from pypy.objspace.std.memoryobject import _buffer_setitem

from rpython.rlib.buffer import Buffer
from rpython.rtyper.annlowlevel import llstr
from rpython.rtyper.lltypesystem import rffi
from rpython.rtyper.lltypesystem.rstr import copy_string_to_raw


class LLBuffer(Buffer):
    _immutable_ = True

    def __init__(self, raw_cdata, size):
        self.raw_cdata = raw_cdata
        self.size = size
        self.readonly = False

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
        return Buffer.getslice(self, start, stop, step, size)

    def setslice(self, start, string):
        raw_cdata = rffi.ptradd(self.raw_cdata, start)
        copy_string_to_raw(llstr(string), raw_cdata, 0, len(string))


# Override the typedef to narrow down the interface that's exposed to app-level

class MiniBuffer(W_Root):
    def __init__(self, buffer, keepalive=None):
        self.buffer = buffer
        self.keepalive = keepalive

    def buffer_w(self, space):
        return self.buffer

    def descr_len(self, space):
        return space.wrap(self.buffer.getlength())

    def descr_getitem(self, space, w_index):
        start, stop, step, size = space.decode_index4(w_index,
                                                      self.buffer.getlength())
        if step == 0:
            return space.wrapbytes(self.buffer.getitem(start))
        res = self.buffer.getslice(start, stop, step, size)
        return space.wrapbytes(res)

    @unwrap_spec(newstring='bufferstr')
    def descr_setitem(self, space, w_index, newstring):
        _buffer_setitem(space, self.buffer, w_index, newstring)


MiniBuffer.typedef = TypeDef(
    "buffer",
    __module__ = "_cffi_backend",
    __len__ = interp2app(MiniBuffer.descr_len),
    __getitem__ = interp2app(MiniBuffer.descr_getitem),
    __setitem__ = interp2app(MiniBuffer.descr_setitem),
    __weakref__ = make_weakref_descr(MiniBuffer),
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
        raise oefmt(space.w_TypeError,
                    "expected a pointer or array cdata, got '%s'", ctype.name)
    if size < 0:
        raise oefmt(space.w_TypeError,
                    "don't know the size pointed to by '%s'", ctype.name)
    return space.wrap(MiniBuffer(LLBuffer(w_cdata._cdata, size), w_cdata))
