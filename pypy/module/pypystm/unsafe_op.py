from pypy.interpreter.gateway import unwrap_spec
from pypy.module._cffi_backend import cdataobj
from rpython.rlib.rstm import stm_ignored
from rpython.rlib.jit import dont_look_inside
from rpython.rtyper.lltypesystem import rffi


@dont_look_inside
def unsafe_write(ptr, value):
    with stm_ignored:
        ptr[0] = value

@unwrap_spec(w_cdata=cdataobj.W_CData, index=int, value='c_int')
def unsafe_write_int32(space, w_cdata, index, value):
    with w_cdata as ptr:
        ptr = rffi.cast(rffi.INTP, rffi.ptradd(ptr, index * 4))
        value = rffi.cast(rffi.INT, value)
        unsafe_write(ptr, value)
