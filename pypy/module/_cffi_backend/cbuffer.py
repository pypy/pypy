from pypy.interpreter.error import oefmt, OperationError
from pypy.interpreter.gateway import unwrap_spec, interp2app
from pypy.interpreter.typedef import TypeDef, make_weakref_descr
from pypy.module._cffi_backend import cdataobj, ctypeptr, ctypearray
from pypy.module._cffi_backend import ctypestruct
from pypy.objspace.std.bufferobject import W_Buffer

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

class MiniBuffer(W_Buffer):
    def __init__(self, buffer, keepalive=None):
        W_Buffer.__init__(self, buffer)
        self.keepalive = keepalive

    def descr_setitem(self, space, w_index, w_obj):
        try:
            W_Buffer.descr_setitem(self, space, w_index, w_obj)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                e.w_type = space.w_ValueError
            raise

@unwrap_spec(w_cdata=cdataobj.W_CData, size=int)
def MiniBuffer___new__(space, w_subtype, w_cdata, size=-1):
    ctype = w_cdata.ctype
    if isinstance(ctype, ctypeptr.W_CTypePointer):
        if size < 0:
            structobj = w_cdata.get_structobj()
            if (structobj is not None and
                isinstance(structobj.ctype, ctypestruct.W_CTypeStructOrUnion)):
                size = structobj._sizeof()
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
    ptr = w_cdata.unsafe_escaping_ptr()    # w_cdata kept alive by MiniBuffer()
    return space.wrap(MiniBuffer(LLBuffer(ptr, size), w_cdata))

MiniBuffer.typedef = TypeDef(
    "_cffi_backend.buffer",
    __new__ = interp2app(MiniBuffer___new__),
    __len__ = interp2app(MiniBuffer.descr_len),
    __getitem__ = interp2app(MiniBuffer.descr_getitem),
    __setitem__ = interp2app(MiniBuffer.descr_setitem),
    __weakref__ = make_weakref_descr(MiniBuffer),
    __str__ = interp2app(MiniBuffer.descr_str),
    __doc__ = """ffi.buffer(cdata[, byte_size]):
Return a read-write buffer object that references the raw C data
pointed to by the given 'cdata'.  The 'cdata' must be a pointer or an
array.  Can be passed to functions expecting a buffer, or directly
manipulated with:

    buf[:]          get a copy of it in a regular string, or
    buf[idx]        as a single character
    buf[:] = ...
    buf[idx] = ...  change the content
""",
    )
MiniBuffer.typedef.acceptable_as_base_class = False
