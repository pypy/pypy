from pypy.interpreter.gateway import unwrap_spec
from pypy.module._cffi_backend import cdataobj
from rpython.rlib.rstm import stm_ignored
from rpython.rtyper.lltypesystem import rffi


@unwrap_spec(w_cdata=cdataobj.W_CData, index=int, value='c_int')
def unsafe_write_int32(space, w_cdata, index, value):
    with w_cdata as ptr:
        ptr = rffi.cast(rffi.INTP, rffi.ptradd(ptr, index * 4))
        value = rffi.cast(rffi.INT, value)
        with stm_ignored:
            ptr[0] = value
