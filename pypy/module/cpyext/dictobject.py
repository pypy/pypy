from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, PyObject
from pypy.module.cpyext.pyerrors import PyErr_BadInternalCall

@cpython_api([], PyObject)
def PyDict_New(space):
    return space.newdict()

@cpython_api([PyObject], rffi.INT)
def PyDict_Check(space, w_obj):
    w_type = space.w_dict
    w_obj_type = space.type(w_obj)
    return space.is_w(w_obj_type, w_type) or space.is_true(space.issubtype(w_obj_type, w_type))


@cpython_api([PyObject, rffi.CCHARP, PyObject], rffi.INT)
def PyDict_SetItemString(space, w_dict, key_ptr, w_obj):
    if PyDict_Check(space, w_dict):
        key = rffi.charp2str(key_ptr)
        # our dicts dont have a standardized interface, so we need
        # to go through the space
        space.setitem(w_dict, space.wrap(key), w_obj)
        return 0
    else:
        PyErr_BadInternalCall()
