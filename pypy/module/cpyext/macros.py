import ctypes

from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, PyObject, make_ref
from pypy.module.cpyext.state import State

# XXX Optimize these functions and put them into macro definitions
@cpython_api([PyObject], lltype.Void)
def Py_DECREF(space, w_obj):
    state = space.fromcache(State)
    obj = state.py_objects_w2r.get(w_obj)
    obj.c_refcnt -= 1
    return

@cpython_api([PyObject], lltype.Void)
def Py_INCREF(space, w_obj):
    state = space.fromcache(State)
    obj = state.py_objects_w2r.get(w_obj)
    obj.c_refcnt += 1
    return
