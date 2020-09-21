from rpython.rlib.nonconst import NonConstant
from rpython.rtyper.lltypesystem import rffi, lltype, ll2ctypes
from rpython.rlib.objectmodel import we_are_translated
from pypy.interpreter.error import OperationError, oefmt
from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal.bridge import BRIDGE
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

@BRIDGE.func("void _hpy_err_SetString(HPyContext ctx, HPy type, const char *message)")
def _hpy_err_SetString(space, ctx, h_exc_type, utf8):
    w_obj = _maybe_utf8_to_w(space, utf8)
    w_exc_type = handles.deref(space, h_exc_type)
    raise OperationError(w_exc_type, w_obj)


@BRIDGE.func("int hpy_err_Occurred_rpy(void)")
def hpy_err_Occurred_rpy(space):
    if we_are_translated():
        # this function should never been called after translation. We can't
        # simply put an assert else the annotator complains that the function
        # returns Void, hack hack hack
        if NonConstant(False):
            return API.int(-42)
        assert False
    #
    # this is a bit of a hack: it will never aim to be correct in 100% of
    # cases, but since it's used only for tests, it's enough.  If an
    # exception was raised by an HPy call, it must be stored in
    # ll2ctypes._callback_exc_info, waiting to be properly re-raised as
    # soon as we exit the C code, by
    # ll2ctypes:get_ctypes_trampoline:invoke_via_ctypes
    res = ll2ctypes._callback_exc_info is not None
    return API.int(res)

@API.func("HPy HPyErr_NoMemory(HPyContext ctx)")
def HPyErr_NoMemory(space, ctx):
    # hack to convince the annotator that this function returns an HPy (i.e.,
    # a Signed)
    if NonConstant(False):
        return -42
    raise OperationError(space.w_MemoryError, space.w_None)
