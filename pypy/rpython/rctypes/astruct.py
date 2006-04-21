from ctypes import Structure
from pypy.annotation.model import SomeCTypesObject, SomeBuiltin
from pypy.rpython import extregistry
from pypy.rpython.lltypesystem import lltype

StructType = type(Structure)


def structtype_specialize_call(hop, **kwds_i):
    from pypy.rpython.error import TyperError
    r_struct = hop.r_result
    v_result = r_struct.allocate_instance(hop.llops)
    index_by_name = {}
    name_by_index = {}
    # collect the keyword arguments
    for key, index in kwds_i.items():
        assert key.startswith('i_')
        name = key[2:]
        assert index not in name_by_index
        index_by_name[name] = index
        name_by_index[index] = name
    # add the positional arguments
    fieldsiter = iter(r_struct.c_data_type._names)
    for i in range(hop.nb_args):
        if i not in name_by_index:
            try:
                name = fieldsiter.next()
            except StopIteration:
                raise TyperError("too many arguments in struct construction")
            if name in index_by_name:
                raise TyperError("multiple values for field %r" % (name,))
            index_by_name[name] = i
            name_by_index[i] = name
    # initialize the fields from the arguments, as far as they are present
    for name in r_struct.c_data_type._names:
        if name in index_by_name:
            index = index_by_name[name]
            v_valuebox = hop.inputarg(r_struct.r_fields[name], arg=index)
            r_struct.setfield(hop.llops, v_result, name, v_valuebox)
    return v_result

def structtype_compute_annotation(metatype, type):
    def compute_result_annotation(*arg_s, **kwds_s):
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
    from pypy.rpython.rctypes.rstruct import StructRepr
    return StructRepr(rtyper, s_struct)

entry = extregistry.register_metatype(StructType,
    compute_annotation=struct_instance_compute_annotation,
    get_repr=structtype_get_repr)
entry.get_field_annotation = struct_instance_field_annotation
