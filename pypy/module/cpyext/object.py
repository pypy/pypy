from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, PyObject, make_ref
from pypy.module.cpyext.typeobject import PyTypeObjectPtr
from pypy.objspace.std.objectobject import W_ObjectObject

def get_cls_for_type_object(space, w_type):
    if space.is_w(w_type, space.w_object):
        return W_ObjectObject
    assert False, "Please add more cases!"

@cpython_api([PyObject], PyObject)
def _PyObject_New(space, w_type):
    cls = get_cls_for_type_object(space, w_type)
    return space.allocate_instance(cls, w_type)

@cpython_api([rffi.VOIDP_real], lltype.Void)
def PyObject_Del(space, w_obj):
    pass # XXX move lltype.free here
