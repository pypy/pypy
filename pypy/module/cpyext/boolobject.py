from rpython.rtyper.lltypesystem import rffi
from pypy.module.cpyext.api import cpython_api, PyObject, LONG_real
from rpython.rlib.rarithmetic import widen

@cpython_api([LONG_real], PyObject)
def PyBool_FromLong(space, value):
    if widen(value) != 0:
        return space.w_True
    return space.w_False
