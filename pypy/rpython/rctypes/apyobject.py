from ctypes import py_object
from pypy.annotation.model import SomeCTypesObject
from pypy.rpython import extregistry
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.robject import pyobj_repr


# __________ py_object() calls __________

def py_object_compute_result_annotation(s_obj=None):
    return SomeCTypesObject(py_object, SomeCTypesObject.OWNSMEMORY)

def py_object_specialize_call(hop):
    r_pyobject = hop.r_result
    v_result = r_pyobject.allocate_instance(hop.llops)
    if len(hop.args_s):
        [v_input] = hop.inputargs(pyobj_repr)
        r_pyobject.setvalue(hop.llops, v_result, v_input)
    return v_result

extregistry.register_value(py_object, 
    compute_result_annotation=py_object_compute_result_annotation,
    specialize_call=py_object_specialize_call)

# __________ prebuilt py_object instances __________

def py_object_instance_compute_annotation(type, instance):
    return SomeCTypesObject(py_object, SomeCTypesObject.OWNSMEMORY)

def py_object_instance_get_repr(rtyper, s_pyobject):
    from pypy.rpython.rctypes.rpyobject import CTypesPyObjRepr
    lowleveltype = lltype.Ptr(lltype.PyObject)
    return CTypesPyObjRepr(rtyper, s_pyobject, lowleveltype)

extregistry.register_type(py_object, 
    compute_annotation=py_object_instance_compute_annotation,
    get_repr=py_object_instance_get_repr)
