from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib.objectmodel import we_are_translated
from pypy.interpreter.error import OperationError, oefmt
from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal import handles
from pypy.module._hpy_universal import llapi
from pypy.module._hpy_universal.interp_unicode import _maybe_utf8_to_w

## HPy exceptions in PyPy
##
## HPy exceptions are implemented using normal RPython exceptions, which means
## that e.g. HPyErr_SetString simply raises an OperationError: see
## e.g. test_exception_transform.test_llhelper_can_raise for a test which
## ensure that exceptions correctly propagate.
##
## Moreover, we need to ensure that it is NOT possible to call RPython code
## when an RPython exception is set, else you get unexpected results. The plan
## is to document that it's forbidden to call most HPy functions if an
## exception has been set, apart for few functions, such as:
##
##     - HPyErr_Occurred()
##     - HPyErr_Fetch()
##     - HPyErr_Clear()
##
## We need to enforce this in debug mode.

@API.func("void HPyErr_SetString(HPyContext ctx, HPy type, const char *message)")
def HPyErr_SetString(space, ctx, h_exc_type, utf8):
    if we_are_translated():
        llapi.pypy_hpy_Err_Clear()
    w_obj = _maybe_utf8_to_w(space, utf8)
    w_exc_type = handles.deref(space, h_exc_type)
    raise OperationError(w_exc_type, w_obj)

@API.func("int HPyErr_Occurred(HPyContext ctx)")
def HPyErr_Occurred(space, ctx):
    if we_are_translated():
        return llapi.pypy_hpy_Err_Occurred()
    else:
        raise NotImplementedError("XXX")
