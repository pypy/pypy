from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rlib.objectmodel import we_are_translated

from pypy.module._ffi_backend import ctypeobj, cdataobj


# ____________________________________________________________

@unwrap_spec(ctype=ctypeobj.W_CType)
def newp(space, ctype, w_init):
    return ctype.newp(w_init)

# ____________________________________________________________

@unwrap_spec(ctype=ctypeobj.W_CType)
def cast(space, ctype, w_ob):
    return ctype.cast(w_ob)

# ____________________________________________________________

def sizeof(space, w_obj):
    ob = space.interpclass_w(w_obj)
    if isinstance(ob, cdataobj.W_CData):
        # xxx CT_ARRAY
        size = ob.ctype.size
    elif isinstance(ob, ctypeobj.W_CType):
        size = ob.size
        if size < 0:
            raise operationerrfmt(space.w_ValueError,
                                  "ctype '%s' is of unknown size",
                                  w_ctype.name)
    else:
        raise OperationError(space.w_TypeError,
                            space.wrap("expected a 'cdata' or 'ctype' object"))
    return space.wrap(size)

@unwrap_spec(ctype=ctypeobj.W_CType)
def alignof(space, ctype):
    align = ctype.alignof()
    if not we_are_translated():
        # obscure hack when untranslated, maybe, approximate, don't use
        assert isinstance(align, llmemory.FieldOffset)
        align = rffi.sizeof(align.TYPE.y)
    return space.wrap(align)
