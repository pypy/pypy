from ctypes import py_object
from pypy.annotation.model import SomeCTypesObject
from pypy.rpython import extregistry


# __________ py_object() calls __________

def py_object_compute_result_annotation(s_obj=None):
    return SomeCTypesObject(py_object, SomeCTypesObject.OWNSMEMORY)

extregistry.register_value(py_object, 
    compute_result_annotation=py_object_compute_result_annotation,
    )#specialize_call=py_object_specialize_call)

# __________ prebuilt py_object instances __________

def py_object_instance_compute_annotation(type, instance):
    return SomeCTypesObject(py_object, SomeCTypesObject.OWNSMEMORY)

extregistry.register_type(py_object, 
    compute_annotation=py_object_instance_compute_annotation)
