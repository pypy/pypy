from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import unwrap_spec
from pypy.rpython.lltypesystem import lltype, rffi

from pypy.module._ffi_backend import ctypeobj


# ____________________________________________________________


PRIMITIVE_TYPES = {}

def eptype(name, TYPE, ctypecls):
    PRIMITIVE_TYPES[name] = ctypecls, rffi.sizeof(TYPE)

eptype("char", lltype.Char, ctypeobj.W_CTypePrimitiveChar)
eptype("signed char", rffi.SIGNEDCHAR, ctypeobj.W_CTypePrimitiveSigned)


@unwrap_spec(name=str)
def new_primitive_type(space, name):
    try:
        ctypecls, size = PRIMITIVE_TYPES[name]
    except KeyError:
        raise OperationError(space.w_KeyError, space.wrap(name))
    return ctypecls(space, name, size)
