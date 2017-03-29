from rpython.rlib import jit
from rpython.rlib.buffer import SubBuffer
from rpython.rlib.rstruct.error import StructError, StructOverflowError
from rpython.rlib.rstruct.formatiterator import CalcSizeFormatIterator

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.typedef import TypeDef, interp_attrproperty
from pypy.module.struct.formatiterator import (
    PackFormatIterator, UnpackFormatIterator
)


class Cache:
    def __init__(self, space):
        self.error = space.new_exception_class("struct.error", space.w_Exception)


def get_error(space):
    return space.fromcache(Cache).error


def _calcsize(space, format):
    fmtiter = CalcSizeFormatIterator()
    try:
        fmtiter.interpret(format)
    except StructOverflowError as e:
        raise OperationError(space.w_OverflowError, space.newtext(e.msg))
    except StructError as e:
        raise OperationError(get_error(space), space.newtext(e.msg))
    return fmtiter.totalsize


@unwrap_spec(format='text')
def calcsize(space, format):
    """Return size of C struct described by format string fmt."""
    return space.newint(_calcsize(space, format))


def _pack(space, format, args_w):
    """Return string containing values v1, v2, ... packed according to fmt."""
    if jit.isconstant(format):
        size = _calcsize(space, format)
    else:
        size = 8
    fmtiter = PackFormatIterator(space, args_w, size)
    try:
        fmtiter.interpret(format)
    except StructOverflowError as e:
        raise OperationError(space.w_OverflowError, space.newtext(e.msg))
    except StructError as e:
        raise OperationError(get_error(space), space.newtext(e.msg))
    return fmtiter.result.build()


@unwrap_spec(format='text')
def pack(space, format, args_w):
    return space.newbytes(_pack(space, format, args_w))


# XXX inefficient
@unwrap_spec(format='text', offset=int)
def pack_into(space, format, w_buffer, offset, args_w):
    """ Pack the values v1, v2, ... according to fmt.
Write the packed bytes into the writable buffer buf starting at offset
    """
    res = _pack(space, format, args_w)
    buf = space.getarg_w('w*', w_buffer)
    if offset < 0:
        offset += buf.getlength()
    size = len(res)
    if offset < 0 or (buf.getlength() - offset) < size:
        raise oefmt(get_error(space),
                    "pack_into requires a buffer of at least %d bytes",
                    size)
    buf.setslice(offset, res)


def _unpack(space, format, buf):
    fmtiter = UnpackFormatIterator(space, buf)
    try:
        fmtiter.interpret(format)
    except StructOverflowError as e:
        raise OperationError(space.w_OverflowError, space.newtext(e.msg))
    except StructError as e:
        raise OperationError(get_error(space), space.newtext(e.msg))
    return space.newtuple(fmtiter.result_w[:])


@unwrap_spec(format='text')
def unpack(space, format, w_str):
    buf = space.getarg_w('s*', w_str)
    return _unpack(space, format, buf)


@unwrap_spec(format='text', offset=int)
def unpack_from(space, format, w_buffer, offset=0):
    """Unpack the buffer, containing packed C structure data, according to
fmt, starting at offset. Requires len(buffer[offset:]) >= calcsize(fmt)."""
    size = _calcsize(space, format)
    buf = space.getarg_w('z*', w_buffer)
    if buf is None:
        raise oefmt(get_error(space), "unpack_from requires a buffer argument")
    if offset < 0:
        offset += buf.getlength()
    if offset < 0 or (buf.getlength() - offset) < size:
        raise oefmt(get_error(space),
                    "unpack_from requires a buffer of at least %d bytes",
                    size)
    buf = SubBuffer(buf, offset, size)
    return _unpack(space, format, buf)


class W_Struct(W_Root):
    _immutable_fields_ = ["format", "size"]

    def __init__(self, space, format):
        self.format = format
        self.size = _calcsize(space, format)

    @unwrap_spec(format='text')
    def descr__new__(space, w_subtype, format):
        self = space.allocate_instance(W_Struct, w_subtype)
        W_Struct.__init__(self, space, format)
        return self

    def descr_pack(self, space, args_w):
        return pack(space, jit.promote_string(self.format), args_w)

    @unwrap_spec(offset=int)
    def descr_pack_into(self, space, w_buffer, offset, args_w):
        return pack_into(space, jit.promote_string(self.format), w_buffer, offset, args_w)

    def descr_unpack(self, space, w_str):
        return unpack(space, jit.promote_string(self.format), w_str)

    @unwrap_spec(offset=int)
    def descr_unpack_from(self, space, w_buffer, offset=0):
        return unpack_from(space, jit.promote_string(self.format), w_buffer, offset)

W_Struct.typedef = TypeDef("Struct",
    __new__=interp2app(W_Struct.descr__new__.im_func),
    format=interp_attrproperty("format", cls=W_Struct, wrapfn="newbytes"),
    size=interp_attrproperty("size", cls=W_Struct, wrapfn="newint"),

    pack=interp2app(W_Struct.descr_pack),
    unpack=interp2app(W_Struct.descr_unpack),
    pack_into=interp2app(W_Struct.descr_pack_into),
    unpack_from=interp2app(W_Struct.descr_unpack_from),
)

def clearcache(space):
    """No-op on PyPy"""
