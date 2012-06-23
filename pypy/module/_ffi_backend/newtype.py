from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import unwrap_spec
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.rarithmetic import ovfcheck

from pypy.module._ffi_backend import ctypeobj


def alignment(TYPE):
    S = lltype.Struct('aligncheck', ('x', lltype.Char), ('y', TYPE))
    return rffi.offsetof(S, 'y')

alignment_of_pointer = alignment(rffi.CCHARP)

# ____________________________________________________________


PRIMITIVE_TYPES = {}

def eptype(name, TYPE, ctypecls):
    PRIMITIVE_TYPES[name] = ctypecls, rffi.sizeof(TYPE), alignment(TYPE)

eptype("char",        lltype.Char,     ctypeobj.W_CTypePrimitiveChar)
eptype("signed char", rffi.SIGNEDCHAR, ctypeobj.W_CTypePrimitiveSigned)
eptype("short",       rffi.SHORT,      ctypeobj.W_CTypePrimitiveSigned)
eptype("int",         rffi.INT,        ctypeobj.W_CTypePrimitiveSigned)
eptype("long",        rffi.LONG,       ctypeobj.W_CTypePrimitiveSigned)
eptype("long long",   rffi.LONGLONG,   ctypeobj.W_CTypePrimitiveSigned)
eptype("unsigned char",      rffi.UCHAR,    ctypeobj.W_CTypePrimitiveUnsigned)
eptype("unsigned short",     rffi.SHORT,    ctypeobj.W_CTypePrimitiveUnsigned)
eptype("unsigned int",       rffi.INT,      ctypeobj.W_CTypePrimitiveUnsigned)
eptype("unsigned long",      rffi.LONG,     ctypeobj.W_CTypePrimitiveUnsigned)
eptype("unsigned long long", rffi.LONGLONG, ctypeobj.W_CTypePrimitiveUnsigned)
eptype("float",  rffi.FLOAT,  ctypeobj.W_CTypePrimitiveFloat)
eptype("double", rffi.DOUBLE, ctypeobj.W_CTypePrimitiveFloat)

@unwrap_spec(name=str)
def new_primitive_type(space, name):
    try:
        ctypecls, size, align = PRIMITIVE_TYPES[name]
    except KeyError:
        raise OperationError(space.w_KeyError, space.wrap(name))
    ctype = ctypecls(space, size, name, len(name), align)
    return ctype

# ____________________________________________________________

@unwrap_spec(ctype=ctypeobj.W_CType)
def new_pointer_type(space, ctype):
    ctypeptr = ctypeobj.W_CTypePointer(space, ctype)
    return ctypeptr

# ____________________________________________________________

@unwrap_spec(ctptr=ctypeobj.W_CType)
def new_array_type(space, ctptr, w_length):
    if not isinstance(ctptr, ctypeobj.W_CTypePointer):
        raise OperationError(space.w_TypeError,
                             space.wrap("first arg must be a pointer ctype"))
    ctitem = ctptr.ctitem
    if ctitem.size < 0:
        raise operationerrfmt(space.w_ValueError,
                              "array item of unknown size: '%s'",
                              ctitem.name)
    if space.is_w(w_length, space.w_None):
        length = -1
        arraysize = -1
        extra = '[]'
    else:
        length = space.getindex_w(w_length, space.w_OverflowError)
        if length < 0:
            raise OperationError(space.w_ValueError,
                                 space.wrap("negative array length"))
        try:
            arraysize = ovfcheck(length * ctitem.size)
        except OverflowError:
            raise OperationError(space.w_OverflowError,
                space.wrap("array size would overflow a ssize_t"))
        extra = '[%d]' % length
    #
    ctypeptr = ctypeobj.W_CTypeArray(space, ctptr, length, arraysize, extra)
    return ctypeptr
