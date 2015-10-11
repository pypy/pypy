import py
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.baseobjspace import W_Root
from pypy.module._cffi_backend import ctypeobj, ctypeptr, cdataobj
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rlib import rweaklist, objectmodel, jit
from rpython.rtyper import annlowlevel


class CffiHandles(rweaklist.RWeakListMixin):
    def __init__(self, space):
        self.initialize()

def get_handles(space):
    return space.fromcache(CffiHandles)

# ____________________________________________________________

@jit.dont_look_inside
def _newp_handle(space, w_ctype, w_x):
    if not objectmodel.we_are_translated():
        py.test.skip("can't test handles untranslated for now")
    new_cdataobj = objectmodel.instantiate(cdataobj.W_CDataHandle,
                                           nonmovable=True)
    gcref = annlowlevel.cast_instance_to_gcref(new_cdataobj)
    _cdata = rffi.cast(rffi.CCHARP, gcref)
    cdataobj.W_CDataHandle.__init__(new_cdataobj, space, _cdata, w_ctype, w_x)
    return new_cdataobj

@unwrap_spec(w_ctype=ctypeobj.W_CType)
def newp_handle(space, w_ctype, w_x):
    if (not isinstance(w_ctype, ctypeptr.W_CTypePointer) or
        not w_ctype.is_void_ptr):
        raise oefmt(space.w_TypeError,
                    "needs 'void *', got '%s'", w_ctype.name)
    return _newp_handle(space, w_ctype, w_x)

@jit.dont_look_inside
def reveal_gcref(ptr):
    return rffi.cast(llmemory.GCREF, ptr)

@unwrap_spec(w_cdata=cdataobj.W_CData)
def from_handle(space, w_cdata):
    ctype = w_cdata.ctype
    if (not isinstance(ctype, ctypeptr.W_CTypePtrOrArray) or
        not ctype.can_cast_anything):
        raise oefmt(space.w_TypeError,
                    "expected a 'cdata' object with a 'void *' out of "
                    "new_handle(), got '%s'", ctype.name)
    with w_cdata as ptr:
        gcref = reveal_gcref(ptr)
    #
    if not gcref:
        raise oefmt(space.w_RuntimeError,
                    "cannot use from_handle() on NULL pointer")
    cd = annlowlevel.cast_gcref_to_instance(W_Root, gcref)
    # force an 'isinstance', to crash clearly if the handle is
    # dead or bogus
    if not isinstance(cd, cdataobj.W_CDataHandle):
        raise oefmt(space.w_SystemError,
                    "ffi.from_handle(): dead or bogus object handle")
    return cd.w_keepalive
