from pypy.rpython.lltypesystem import rffi, lltype
from pypy.interpreter.error import OperationError
from pypy.module.cpyext.api import cpython_api, PyObject, make_ref


@cpython_api([PyObject, rffi.CCHARP], lltype.Void)
def PyErr_SetString(space, w_type, message_ptr):
    message = rffi.charp2str(message_ptr)
    w_obj = space.call_function(w_type, space.wrap(message))
    raise OperationError(w_type, w_obj)


@cpython_api([], lltype.Void)
def PyErr_BadInternalCall(space):
    raise OperationError(space.w_SystemError, space.wrap("Bad internal call!"))

