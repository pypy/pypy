from ctypes import ARRAY, c_int, c_char
from pypy.annotation.model import SomeCTypesObject, SomeBuiltin, SomeString
from pypy.rpython import extregistry
from pypy.rpython.lltypesystem import lltype

ArrayType = type(ARRAY(c_int, 10))

def arraytype_specialize_call(hop):
    r_array = hop.r_result
    return r_array.allocate_instance(hop.llops)

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

entry = extregistry.register_metatype(ArrayType,
    compute_annotation=array_instance_compute_annotation,
    get_repr=arraytype_get_repr)
def char_array_get_field_annotation(s_array, fieldname):
    assert fieldname == 'value'
    if s_array.knowntype._type_ != c_char:
        raise Exception("only arrays of chars have a .value attribute")
    return SomeString()   # can_be_None = False
entry.get_field_annotation = char_array_get_field_annotation
