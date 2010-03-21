from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, PyObject, make_ref
from pypy.module.cpyext.typeobject import PyTypeObjectPtr, W_PyCTypeObject, W_PyCObject
from pypy.objspace.std.objectobject import W_ObjectObject


@cpython_api([PyObject], PyObject)
def _PyObject_New(space, w_type):
    if isinstance(w_type, W_PyCTypeObject):
        w_pycobj = space.allocate_instance(W_PyCObject, w_type)
        return w_pycobj
    assert False, "Please add more cases in get_cls_for_type_object!"

@cpython_api([rffi.VOIDP_real], lltype.Void)
def PyObject_Del(space, w_obj):
    pass # XXX move lltype.free here
