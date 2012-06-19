from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import unwrap_spec
from pypy.rpython.lltypesystem import lltype, rffi

from pypy.module._ffi_backend import ctypeobj


# ____________________________________________________________


PRIMITIVE_TYPES = {}

def eptype(name, TYPE, ctypecls):
    size = rffi.sizeof(TYPE)
    if ctypecls is ctypeobj.W_CTypePrimitiveSigned:
        value_fits_long = size <= rffi.sizeof(lltype.Signed)
    elif ctypecls is ctypeobj.W_CTypePrimitiveUnsigned:
        value_fits_long = size < rffi.sizeof(lltype.Signed)
    else:
        value_fits_long = False
    PRIMITIVE_TYPES[name] = ctypecls, size, value_fits_long

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


@unwrap_spec(name=str)
def new_primitive_type(space, name):
    try:
        ctypecls, size, value_fits_long = PRIMITIVE_TYPES[name]
    except KeyError:
        raise OperationError(space.w_KeyError, space.wrap(name))
    ctype = ctypecls(space, name, size)
    ctype.value_fits_long = value_fits_long
    return ctype
