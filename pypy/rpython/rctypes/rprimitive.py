from ctypes import c_char, c_byte, c_ubyte, c_short, c_ushort, c_int, c_uint
from ctypes import c_long, c_ulong, c_longlong, c_ulonglong, c_float
from ctypes import c_double, c_char_p
from pypy.annotation import model as annmodel
from pypy.rpython import extregistry
from pypy.rpython.rmodel import Repr, inputconst
from pypy.rpython.lltypesystem import lltype
from pypy.annotation.pairtype import pairtype
from pypy.rpython.rmodel import IntegerRepr, FloatRepr, CharRepr
from pypy.rpython.error import TyperError
from pypy.rpython.rctypes.rmodel import CTypesValueRepr

ctypes_annotation_list = {
    c_char:          lltype.Char,
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

class PrimitiveRepr(CTypesValueRepr):

    def return_c_data(self, llops, v_c_data):
        """Read out the atomic data from a raw C pointer.
        Used when the data is returned from an operation or C function call.
        """
        return self.getvalue_from_c_data(llops, v_c_data)

    def return_value(self, llops, v_value):
        # like return_c_data(), but when the input is only the value
        # field instead of the c_data pointer
        return v_value

    def rtype_getattr(self, hop):
        s_attr = hop.args_s[1]
        assert s_attr.is_constant()
        assert s_attr.const == 'value'
        v_primitive = hop.inputarg(self, 0)
        return self.getvalue(hop.llops, v_primitive)

    def rtype_setattr(self, hop):
        s_attr = hop.args_s[1]
        assert s_attr.is_constant()
        assert s_attr.const == 'value'
        v_primitive, v_attr, v_value = hop.inputargs(self, lltype.Void,
                                                        self.ll_type)
        self.setvalue(hop.llops, v_primitive, v_value)


class __extend__(pairtype(IntegerRepr, PrimitiveRepr),
                 pairtype(FloatRepr, PrimitiveRepr),
                 pairtype(CharRepr, PrimitiveRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        # first convert 'v' to the precise expected low-level type
        r_input = r_to.rtyper.primitive_to_repr[r_to.ll_type]
        v = llops.convertvar(v, r_from, r_input)
        # allocate a memory-owning box to hold a copy of the ll value 'v'
        r_temp = r_to.r_memoryowner
        v_owned_box = r_temp.allocate_instance(llops)
        r_temp.setvalue(llops, v_owned_box, v)
        # return this box possibly converted to the expected output repr,
        # which might be a memory-aliasing box
        return llops.convertvar(v_owned_box, r_temp, r_to)


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
