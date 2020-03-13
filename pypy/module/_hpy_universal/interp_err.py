from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.interpreter.error import OperationError, oefmt
from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal import handles
from pypy.module._hpy_universal.interp_unicode import _maybe_utf8_to_w

@API.func("void HPyErr_SetString(HPyContext ctx, HPy type, const char *message)")
def HPyErr_SetString(space, ctx, h_exc_type, utf8):
   w_obj = _maybe_utf8_to_w(space, utf8)
   w_exc_type = handles.deref(space, h_exc_type)
   raise OperationError(w_exc_type, w_obj)

@API.func("int HPyErr_Occurred(HPyContext ctx)")
def HPyErr_Occurred(space, ctx):
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return 0
    raise NotImplementedError
