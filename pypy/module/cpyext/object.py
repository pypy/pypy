from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, PyObject, make_ref
from pypy.module.cpyext.typeobject import PyTypeObjectPtr

@cpython_api([PyTypeObjectPtr], PyObject)
def _PyObject_New(space, pto):
    return space.wrap(42) # XXX

@cpython_api([rffi.VOIDP_real], lltype.Void)
def PyObject_Del(space, w_obj):
    pass # XXX move lltype.free here
