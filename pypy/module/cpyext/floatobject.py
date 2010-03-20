from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, PyObject, make_ref

@cpython_api([lltype.Float], PyObject)
def PyFloat_FromDouble(space, value):
    return space.wrap(value)

@cpython_api([PyObject], lltype.Float)
def PyFloat_AsDouble(space, w_obj):
    return space.float_w(space.float(w_obj))
