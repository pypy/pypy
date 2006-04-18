from ctypes import c_char, c_byte, c_ubyte, c_short, c_ushort, c_int, c_uint
from ctypes import c_long, c_ulong, c_longlong, c_ulonglong, c_float
from ctypes import c_double, c_wchar, c_char_p
from pypy.annotation import model as annmodel
from pypy.rpython import extregistry
from pypy.rpython.lltypesystem import lltype

ctypes_annotation_list = {
    c_char:          lltype.Char,
    c_wchar:         lltype.UniChar,
    c_byte:          lltype.Signed,
    c_ubyte:         lltype.Unsigned,
    c_short:         lltype.Signed,
    c_ushort:        lltype.Unsigned,
    c_int:           lltype.Signed,
    c_uint:          lltype.Unsigned,
    c_long:          lltype.Signed,
    c_ulong:         lltype.Unsigned,
    c_longlong:      lltype.SignedLongLong,
    c_ulonglong:     lltype.UnsignedLongLong,
    c_float:         lltype.Float,
    c_double:        lltype.Float,
}.items()   # nb. platform-dependent duplicate ctypes are removed


def primitive_specialize_call(hop):
    r_primitive = hop.r_result
    v_result = r_primitive.allocate_instance(hop.llops)
    if len(hop.args_s):
        v_value, = hop.inputargs(r_primitive.ll_type)
        r_primitive.setvalue(hop.llops, v_result, v_value)
    return v_result

def do_register(the_type, ll_type):
    def compute_result_annotation_function(s_arg=None):
        return annmodel.SomeCTypesObject(the_type,
                annmodel.SomeCTypesObject.OWNSMEMORY)

    extregistry.register_value(the_type,
        compute_result_annotation=compute_result_annotation_function,
        specialize_call=primitive_specialize_call
        )

    def compute_prebuilt_instance_annotation(the_type, instance):
        return annmodel.SomeCTypesObject(the_type,
                annmodel.SomeCTypesObject.OWNSMEMORY)

    def primitive_get_repr(rtyper, s_primitive):
        from pypy.rpython.rctypes.rprimitive import PrimitiveRepr
        return PrimitiveRepr(rtyper, s_primitive, ll_type)

    entry = extregistry.register_type(the_type,
            compute_annotation=compute_prebuilt_instance_annotation,
            get_repr=primitive_get_repr,
            )
    s_value_annotation = annmodel.lltype_to_annotation(ll_type)
    def primitive_get_field_annotation(s_primitive, fieldname):
        assert fieldname == 'value'
        return s_value_annotation
    entry.get_field_annotation = primitive_get_field_annotation
    entry.s_return_trick = s_value_annotation

for the_type, ll_type in ctypes_annotation_list:
    do_register(the_type, ll_type)
