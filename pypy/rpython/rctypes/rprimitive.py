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

def do_register(the_type, ll_type):
    def annotation_function(s_arg):
        return annmodel.SomeCTypesObject(the_type,
                annmodel.SomeCTypesObject.OWNSMEMORY)

    extregistry.register_value(the_type,
        compute_result_annotation=annotation_function)
    entry = extregistry.register_type(the_type)
    entry.fields_s = {'value': annmodel.lltype_to_annotation(ll_type)}

for the_type, ll_type in ctypes_annotation_list:
    do_register(the_type, ll_type)

#extregistry.register_type(ArrayType, 
#    compute_annotation=arraytype_compute_annotation,
#    specialize_call=arraytype_specialize_call)

#def arraytype_get_repr(rtyper, s_array):
#    return ArrayRepr(rtyper, s_array.knowntype)
#extregistry.register_metatype(ArrayType, get_repr=arraytype_get_repr)
