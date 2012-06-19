from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.rpython.lltypesystem import lltype, rffi

from pypy.module._ffi_backend.ctypeobj import W_CType


# ____________________________________________________________

@unwrap_spec(ctype=W_CType)
def cast(space, ctype, w_ob):
    return ctype.cast(w_ob)
