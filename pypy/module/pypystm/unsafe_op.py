from pypy.interpreter.gateway import unwrap_spec
from pypy.module._cffi_backend import cdataobj
from rpython.rtyper.lltypesystem import lltype, rffi


UNSAFE_INT = lltype.Struct('UNSAFE_INT', ('x', rffi.INT),
                           hints = {'stm_dont_track_raw_accesses': True})
UNSAFE_INT_P = lltype.Ptr(UNSAFE_INT)


@unwrap_spec(w_cdata=cdataobj.W_CData, index=int, value='c_int')
def unsafe_write_int32(space, w_cdata, index, value):
    with w_cdata as ptr:
        ptr = rffi.cast(UNSAFE_INT_P, rffi.ptradd(ptr, index * 4))
        ptr.x = rffi.cast(rffi.INT, value)
