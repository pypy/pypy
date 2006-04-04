from ctypes import c_char, c_byte, c_ubyte, c_short, c_ushort, c_int, c_uint
from ctypes import c_long, c_ulong, c_longlong, c_ulonglong, c_float
from ctypes import c_double, c_char_p
from pypy.annotation import model as annmodel
from pypy.rpython import extregistry
from pypy.rpython.rmodel import Repr, inputconst
from pypy.rpython.lltypesystem import lltype
from pypy.annotation.pairtype import pairtype
from pypy.rpython.rmodel import IntegerRepr
from pypy.rpython.rctypes.rmodel import CTypesValueRepr

ctypes_annotation_list = [
    (c_char,          lltype.Char),
    (c_byte,          lltype.Signed),
    (c_ubyte,         lltype.Unsigned),
    (c_short,         lltype.Signed),
    (c_ushort,        lltype.Unsigned),
    (c_int,           lltype.Signed),
    (c_uint,          lltype.Unsigned),
    (c_long,          lltype.Signed),
    (c_ulong,         lltype.Unsigned),
    (c_longlong,      lltype.SignedLongLong),
    (c_ulonglong,     lltype.UnsignedLongLong),
    (c_float,         lltype.Float),
    (c_double,        lltype.Float),
]

class PrimitiveRepr(CTypesValueRepr):

    def convert_const(self, ctype_value):
        assert isinstance(ctype_value, self.ctype)
        key = id(ctype_value)
        try:
            return self.const_cache[key][0]
        except KeyError:
            p = lltype.malloc(self.lowleveltype.TO)
            
            self.const_cache[key] = p, ctype_value
            p.c_data.value = ctype_value.value
            return p
        
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

# need to extend primitive repr to implement convert_from_to() for various
# conversions, firstly the conversion from c_long() to Signed

class __extend__(pairtype(PrimitiveRepr, IntegerRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        assert r_from.ll_type == r_to.lowleveltype

        return r_from.getvalue(llops, v)

def primitive_specialize_call(hop):
    r_primitive = hop.r_result
    c1 = hop.inputconst(lltype.Void, r_primitive.lowleveltype.TO) 
    v_result = hop.genop("malloc", [c1], resulttype=r_primitive.lowleveltype)
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
    def primitive_get_field_annotation(s_primitive, fieldname):
        assert fieldname == 'value'
        return annmodel.lltype_to_annotation(ll_type)
    entry.get_field_annotation = primitive_get_field_annotation
    entry.lowleveltype = ll_type

for the_type, ll_type in ctypes_annotation_list:
    do_register(the_type, ll_type)
