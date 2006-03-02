from ctypes import c_char, c_byte, c_ubyte, c_short, c_ushort, c_int, c_uint
from ctypes import c_long, c_ulong, c_longlong, c_ulonglong, c_float
from ctypes import c_double, c_char_p
from pypy.annotation import model as annmodel
from pypy.rpython import extregistry
from pypy.rpython.rmodel import Repr
from pypy.rpython.lltypesystem import lltype
from pypy.annotation.pairtype import pairtype
from pypy.rpython.rmodel import IntegerRepr

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

class PrimitiveRepr(Repr):
    def __init__(self, rtyper, type, ll_type):
        self.ll_type = ll_type
        self.lowleveltype = lltype.Ptr(
            lltype.GcStruct( "CtypesBox_%s" % (type.__name__,),
                ( "c_data", lltype.Struct('C_Data_%s' % (type.__name__,),
                    ('value', ll_type) )
                )
            )
        )

    def rtype_getattr(self, hop):
        s_attr = hop.args_s[1]
        assert s_attr.is_constant()
        assert s_attr.const == 'value'
        v_primitive = hop.inputarg(self, 0)
        cname = hop.inputconst(lltype.Void, 'value')
        inputargs = [v_primitive, hop.inputconst(lltype.Void, "c_data")]
        v_c_data = hop.genop('getsubstruct',
                    inputargs,
                    lltype.Ptr(self.lowleveltype.TO.c_data) )

        return hop.genop('getfield', [v_c_data, cname],
                resulttype=self.ll_type)


def primitive_specialize_call(hop):
    r_primitive = hop.r_result
    c1 = hop.inputconst(lltype.Void, r_primitive.lowleveltype.TO) 
    v_result = hop.genop("malloc", [c1], resulttype=r_primitive.lowleveltype)
    inputargs = [v_result, hop.inputconst(lltype.Void, "c_data")]
    v_c_data = hop.genop('getsubstruct',
                inputargs,
                lltype.Ptr(r_primitive.lowleveltype.TO.c_data) )
    cname = hop.inputconst(lltype.Void, 'value')
    if len(hop.args_s):
        v_value, = hop.inputargs(r_primitive.ll_type)

        hop.genop('setfield', [v_c_data, cname, v_value])
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
        return PrimitiveRepr(rtyper, s_primitive.knowntype, ll_type)

    entry = extregistry.register_type(the_type,
            compute_annotation=compute_prebuilt_instance_annotation,
            get_repr=primitive_get_repr,
            )
    entry.fields_s = {'value': annmodel.lltype_to_annotation(ll_type)}
    entry.lowleveltype = ll_type

for the_type, ll_type in ctypes_annotation_list:
    do_register(the_type, ll_type)
