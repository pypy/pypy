from ctypes import ARRAY, c_int
from pypy.annotation.model import SomeCTypesObject, SomeBuiltin
from pypy.rpython import extregistry
from pypy.rpython.lltypesystem import lltype

ArrayType = type(ARRAY(c_int, 10))

def arraytype_specialize_call(hop):
    r_array = hop.r_result
    return hop.genop("malloc", [
        hop.inputconst(lltype.Void, r_array.lowleveltype.TO), 
        ], resulttype=r_array.lowleveltype,
    )

def arraytype_compute_annotation(metatype, type):
    def compute_result_annotation(*arg_s):
        return SomeCTypesObject(type, SomeCTypesObject.OWNSMEMORY)
    return SomeBuiltin(compute_result_annotation, methodname=type.__name__)

extregistry.register_type(ArrayType, 
    compute_annotation=arraytype_compute_annotation,
    specialize_call=arraytype_specialize_call)

def array_instance_compute_annotation(type, instance):
    return SomeCTypesObject(type, SomeCTypesObject.OWNSMEMORY)

def arraytype_get_repr(rtyper, s_array):
    from pypy.rpython.rctypes.rarray import ArrayRepr
    return ArrayRepr(rtyper, s_array)

extregistry.register_metatype(ArrayType,
    compute_annotation=array_instance_compute_annotation,
    get_repr=arraytype_get_repr)
