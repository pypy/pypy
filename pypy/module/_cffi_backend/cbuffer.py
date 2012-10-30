from pypy.interpreter.error import operationerrfmt
from pypy.interpreter.buffer import RWBuffer
from pypy.interpreter.gateway import unwrap_spec, interp2app
from pypy.interpreter.typedef import TypeDef
from pypy.rpython.lltypesystem import rffi
from pypy.module._cffi_backend import cdataobj, ctypeptr, ctypearray


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

LLBuffer.typedef = TypeDef(
    "buffer",
    __module__ = "_cffi_backend",
    __len__ = interp2app(RWBuffer.descr_len),
    __getitem__ = interp2app(RWBuffer.descr_getitem),
    __setitem__ = interp2app(RWBuffer.descr_setitem),
    __buffer__ = interp2app(RWBuffer.descr__buffer__),
    )
LLBuffer.typedef.acceptable_as_base_class = False


@unwrap_spec(cdata=cdataobj.W_CData, size=int)
def buffer(space, cdata, size=-1):
    ctype = cdata.ctype
    if isinstance(ctype, ctypeptr.W_CTypePointer):
        if size < 0:
            size = ctype.ctitem.size
    elif isinstance(ctype, ctypearray.W_CTypeArray):
        if size < 0:
            size = cdata._sizeof()
    else:
        raise operationerrfmt(space.w_TypeError,
                              "expected a pointer or array cdata, got '%s'",
                              ctype.name)
    if size < 0:
        raise operationerrfmt(space.w_TypeError,
                              "don't know the size pointed to by '%s'",
                              ctype.name)
    return space.wrap(LLBuffer(cdata._cdata, size))
