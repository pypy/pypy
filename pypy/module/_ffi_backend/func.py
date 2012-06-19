from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.rpython.lltypesystem import lltype, rffi

from pypy.module._ffi_backend import ctypeobj, cdataobj


# ____________________________________________________________

@unwrap_spec(ctype=ctypeobj.W_CType)
def cast(space, ctype, w_ob):
    return ctype.cast(w_ob)

# ____________________________________________________________

def sizeof(space, w_obj):
    if cdataobj.check_cdata(space, w_obj):
        # xxx CT_ARRAY
        w_cdata = space.interp_w(cdataobj.W_CData, w_obj)
        size = w_cdata.ctype.size
    elif ctypeobj.check_ctype(space, w_obj):
        w_ctype = space.interp_w(ctypeobj.W_CType, w_obj)
        size = w_ctype.size
        if size < 0:
            raise operationerrfmt(space.w_ValueError,
                                  "ctype '%s' is of unknown size",
                                  w_ctype.name)
    else:
        raise OperationError(space.w_TypeError,
                            space.wrap("expected a 'cdata' or 'ctype' object"))
    return space.wrap(size)
