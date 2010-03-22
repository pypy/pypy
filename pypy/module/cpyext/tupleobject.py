from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, PyObject, Py_ssize_t
from pypy.module.cpyext.macros import Py_DECREF
from pypy.objspace.std.tupleobject import W_TupleObject


@cpython_api([Py_ssize_t], PyObject)
def PyTuple_New(space, size):
    return space.newtuple([space.w_None] * size)

@cpython_api([PyObject, Py_ssize_t, PyObject], rffi.INT_real)
def PyTuple_SetItem(space, w_t, pos, w_obj):
    assert isinstance(w_t, W_TupleObject)
    w_t.wrappeditems[pos] = w_obj
    Py_DECREF(space, w_obj) # SetItem steals a reference!
    return 0
