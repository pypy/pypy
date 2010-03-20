from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, PyObject, make_ref
from pypy.module.cpyext.typeobject import PyTypeObjectPtr

@cpython_api([PyTypeObjectPtr], PyObject)
def _PyObject_New(space, pto):
    return space.wrap(42)
