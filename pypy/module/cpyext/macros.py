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
    if obj.c_refcnt == 0:
        del state.py_objects_w2r[w_obj]
        ptr = ctypes.addressof(obj._obj._storage)
        del state.py_objects_r2w[ptr]
        # XXX this will likely be somewhere else when we have grown a type object
        lltype.free(obj)
    else:
        assert obj.c_refcnt > 0
    return

@cpython_api([PyObject], lltype.Void)
def Py_INCREF(space, w_obj):
    state = space.fromcache(State)
    obj = state.py_objects_w2r.get(w_obj)
    obj.c_refcnt += 1
    return
