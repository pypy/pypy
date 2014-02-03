import weakref
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import unwrap_spec
from pypy.module._cffi_backend import ctypeobj, ctypeptr, cdataobj
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib import rweaklist


class CffiHandles(rweaklist.RWeakListMixin):
    def __init__(self, space):
        self.initialize()

def get(space):
    return space.fromcache(CffiHandles)

# ____________________________________________________________

@unwrap_spec(w_ctype=ctypeobj.W_CType)
def newp_handle(space, w_ctype, w_x):
    if (not isinstance(w_ctype, ctypeptr.W_CTypePointer) or
        not w_ctype.is_void_ptr):
        raise oefmt(space.w_TypeError,
                    "needs 'void *', got '%s'", w_ctype.name)
    index = get(space).reserve_next_handle_index()
    _cdata = rffi.cast(rffi.CCHARP, index + 1)
    new_cdataobj = cdataobj.W_CDataHandle(space, _cdata, w_ctype, w_x)
    get(space).store_handle(index, new_cdataobj)
    return new_cdataobj

@unwrap_spec(w_cdata=cdataobj.W_CData)
def from_handle(space, w_cdata):
    ctype = w_cdata.ctype
    if (not isinstance(ctype, ctypeptr.W_CTypePtrOrArray) or
        not ctype.can_cast_anything):
        raise oefmt(space.w_TypeError,
                    "expected a 'cdata' object with a 'void *' out of "
                    "new_handle(), got '%s'", ctype.name)
    index = rffi.cast(lltype.Signed, w_cdata._cdata)
    original_cdataobj = get(space).fetch_handle(index - 1)
    #
    if isinstance(original_cdataobj, cdataobj.W_CDataHandle):
        return original_cdataobj.w_keepalive
    else:
        if index == 0:
            msg = "cannot use from_handle() on NULL pointer"
        else:
            msg = "'void *' value does not correspond to any object"
        raise OperationError(space.w_RuntimeError, space.wrap(msg))
