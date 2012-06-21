from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import unwrap_spec
from pypy.rpython.lltypesystem import lltype, rffi

from pypy.module._ffi_backend import ctypeobj


# ____________________________________________________________


PRIMITIVE_TYPES = {}

def eptype(name, TYPE, ctypecls):
    PRIMITIVE_TYPES[name] = ctypecls, rffi.sizeof(TYPE)

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
        ctypecls, size = PRIMITIVE_TYPES[name]
    except KeyError:
        raise OperationError(space.w_KeyError, space.wrap(name))
    ctype = ctypecls(space, size, name, len(name))
    return ctype

# ____________________________________________________________

@unwrap_spec(ctype=ctypeobj.W_CType)
def new_pointer_type(space, ctype):
    ctypeptr = ctypeobj.W_CTypePointer(space, ctype)
    return ctypeptr
