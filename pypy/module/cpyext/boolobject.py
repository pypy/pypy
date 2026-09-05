from rpython.rtyper.lltypesystem import rffi
from pypy.module.cpyext.api import cpython_api, PyObject
from rpython.rlib.rarithmetic import widen

@cpython_api([rffi.LONG], PyObject, abi3=True)
def PyBool_FromLong(space, value):
    if widen(value) != 0:
        return space.w_True
    return space.w_False

@cpython_api([PyObject], rffi.INT_real, error=-1, abi3=True, noheader=True)
def Py_IsTrue(space, w_obj):
    return int(space.is_w(w_obj, space.w_True))

@cpython_api([PyObject], rffi.INT_real, error=-1, abi3=True, noheader=True)
def Py_IsFalse(space, w_obj):
    return int(space.is_w(w_obj, space.w_False))
