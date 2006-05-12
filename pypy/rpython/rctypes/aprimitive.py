from ctypes import c_char, c_byte, c_ubyte, c_short, c_ushort, c_int, c_uint
from ctypes import c_long, c_ulong, c_longlong, c_ulonglong, c_float
from ctypes import c_double, c_wchar, c_char_p
from pypy.annotation import model as annmodel
from pypy.rpython.rctypes.implementation import CTypesCallEntry, CTypesObjEntry
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.rctypes import rcarithmetic as rcarith

ctypes_annotation_list = {
    c_char:          lltype.Char,
    c_wchar:         lltype.UniChar,
    c_byte:          rcarith.CByte,
    c_ubyte:         rcarith.CUByte,
    c_short:         rcarith.CShort,
    c_ushort:        rcarith.CUShort,
    c_int:           rcarith.CInt,
    c_uint:          rcarith.CUInt,
    c_long:          rcarith.CLong,
    c_ulong:         rcarith.CULong,
    c_longlong:      rcarith.CLonglong,
    c_ulonglong:     rcarith.CULonglong,
    c_float:         lltype.Float,
    c_double:        lltype.Float,
}   # nb. platform-dependent duplicate ctypes are removed

def return_lltype(c_type):
    ll_type = ctypes_annotation_list[c_type]
    if isinstance(ll_type, lltype.Number):
        return ll_type.normalized()
    return ll_type

class CallEntry(CTypesCallEntry):
    "Annotation and rtyping of calls to primitive c_xxx types."

    def specialize_call(self, hop):
        r_primitive = hop.r_result
        hop.exception_cannot_occur()
        v_result = r_primitive.allocate_instance(hop.llops)
        if len(hop.args_s):
            v_value, = hop.inputargs(r_primitive.ll_type)
            r_primitive.setvalue(hop.llops, v_result, v_value)
        return v_result


class ObjEntry(CTypesObjEntry):
    "Annotation and rtyping of instances of the primitive c_xxx type."

    def get_repr(self, rtyper, s_primitive):
        from pypy.rpython.rctypes.rprimitive import PrimitiveRepr
        ll_type = ctypes_annotation_list[self.type]
        return PrimitiveRepr(rtyper, s_primitive, ll_type)

    def get_field_annotation(self, s_primitive, fieldname):
        assert fieldname == 'value'
        return self.get_s_value()

    def get_s_value(self):
        ll_type = return_lltype(self.type)
        return annmodel.lltype_to_annotation(ll_type)

    s_return_trick = property(get_s_value)


for _ctype in ctypes_annotation_list:
    CallEntry._register_value(_ctype)
    ObjEntry._register_type(_ctype)
