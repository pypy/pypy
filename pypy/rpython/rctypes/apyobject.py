from ctypes import py_object
from pypy.annotation.model import SomeCTypesObject
from pypy.rpython import extregistry


def py_object_compute_result_annotation(s_obj=None):
    return SomeCTypesObject(py_object, SomeCTypesObject.OWNSMEMORY)

extregistry.register_value(py_object, 
    compute_result_annotation=py_object_compute_result_annotation,
    )#specialize_call=py_object_specialize_call)
