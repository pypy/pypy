from pypy.module.cpyext.api import cpython_api
from pypy.module.cpyext.pyobject import PyObject

@cpython_api([PyObject], PyObject)
def PyMemoryView_FromObject(space, w_obj):
    return space.call_method(space.builtin, "memoryview", w_obj)
