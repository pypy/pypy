from ctypes import ARRAY, c_int, c_char
from pypy.annotation.model import SomeCTypesObject, SomeBuiltin, SomeString
from pypy.rpython import extregistry
from pypy.rpython.lltypesystem import lltype

ArrayType = type(ARRAY(c_int, 10))

def arraytype_specialize_call(hop):
    from pypy.rpython.error import TyperError
    from pypy.rpython.rmodel import inputconst
    r_array = hop.r_result
    v_result = r_array.allocate_instance(hop.llops)
    if hop.nb_args > r_array.length:
        raise TyperError("too many arguments for an array of length %d" % (
            r_array.length,))
    for i in range(hop.nb_args):
        v_item = hop.inputarg(r_array.r_item, arg=i)
        c_index = inputconst(lltype.Signed, i)
        r_array.setitem(hop.llops, v_result, c_index, v_item)
    return v_result

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
