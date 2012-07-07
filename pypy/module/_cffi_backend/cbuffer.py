from pypy.interpreter.error import operationerrfmt
from pypy.interpreter.buffer import RWBuffer
from pypy.interpreter.gateway import unwrap_spec
from pypy.rpython.lltypesystem import rffi
from pypy.module._cffi_backend import cdataobj, ctypeptr


class LLBuffer(RWBuffer):

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


@unwrap_spec(cdata=cdataobj.W_CData, size=int)
def buffer(space, cdata, size=-1):
    if not isinstance(cdata.ctype, ctypeptr.W_CTypePtrOrArray):
        raise operationerrfmt(space.w_TypeError,
                              "expected a pointer or array cdata, got '%s'",
                              cdata.ctype.name)
    if size < 0:
        size = cdata._sizeof()
        if size < 0:
            raise operationerrfmt(space.w_TypeError,
                                  "don't know the size pointed to by '%s'",
                                  cdata.ctype.name)
    return space.wrap(LLBuffer(cdata._cdata, size))
