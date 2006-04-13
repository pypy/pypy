from ctypes import Structure
from pypy.annotation.model import SomeCTypesObject, SomeBuiltin
from pypy.rpython import extregistry
from pypy.rpython.rctypes.rmodel import CTypesRefRepr, CTypesValueRepr

StructType = type(Structure)




def structtype_specialize_call(hop):
    r_struct = hop.r_result
    return hop.genop("malloc", [
        hop.inputconst(lltype.Void, r_struct.lowleveltype.TO), 
        ], resulttype=r_struct.lowleveltype,
    )

def structtype_compute_annotation(metatype, type):
    def compute_result_annotation(*arg_s):
        return SomeCTypesObject(type, SomeCTypesObject.OWNSMEMORY)
    return SomeBuiltin(compute_result_annotation, methodname=type.__name__)

extregistry.register_type(StructType, 
    compute_annotation=structtype_compute_annotation,
    specialize_call=structtype_specialize_call)

def struct_instance_compute_annotation(type, instance):
    return SomeCTypesObject(type, SomeCTypesObject.OWNSMEMORY)

def struct_instance_field_annotation(s_struct, fieldname):
    structtype = s_struct.knowntype
    for name, ctype in structtype._fields_:
        if name == fieldname:
            s_result = SomeCTypesObject(ctype, SomeCTypesObject.MEMORYALIAS)
            return s_result.return_annotation()
    raise AttributeError('%r has no field %r' % (structtype, fieldname))

def structtype_get_repr(rtyper, s_struct):
    return StructRepr(rtyper, s_struct)

entry = extregistry.register_metatype(StructType,
    compute_annotation=struct_instance_compute_annotation,
    get_repr=structtype_get_repr)
entry.get_field_annotation = struct_instance_field_annotation
