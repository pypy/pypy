from ctypes import ARRAY, c_int
from pypy.annotation.model import SomeCTypesObject, SomeBuiltin
from pypy.rpython import extregistry
from pypy.rpython.rmodel import Repr
from pypy.rpython.lltypesystem import lltype
from pypy.annotation.pairtype import pairtype
from pypy.rpython.rmodel import IntegerRepr

ArrayType = type(ARRAY(c_int, 10))

def arraytype_compute_annotation(metatype, type):
    def compute_result_annotation(*arg_s):
        return SomeCTypesObject(type, SomeCTypesObject.OWNSMEMORY)
    return SomeBuiltin(compute_result_annotation,
        methodname=type.__name__)


class ArrayRepr(Repr):
    def __init__(self, rtyper, type):
        
        item_ctype = type._type_
        self.length = type._length_
        
        entry = extregistry.lookup_type(item_ctype)
        self.r_item = entry.get_repr(rtyper, item_ctype)
        
        self.lowleveltype = lltype.Ptr(
            lltype.GcStruct( "CtypesGcArray_%s" % type.__name__,
                ( "c_data", lltype.Array(self.r_item.lowleveltype, 
                    hints={"nolength": True})
                )
            )
        )

class __extend__(pairtype(ArrayRepr, IntegerRepr)):
    def rtype_setitem((r_array, r_int), hop):
        v_array, v_index, v_item = hop.inputargs(r_array, lltype.Signed,
                r_array.r_item)
        inputargs = [v_array, hop.inputconst(lltype.Void, "c_data")]
        v_c_data = hop.genop('getsubstruct',
                    inputargs,
                    lltype.Ptr(r_array.lowleveltype.TO.c_data) )
        hop.genop('setarrayitem', [v_c_data, v_index, v_item])

    def rtype_getitem((r_array, r_int), hop):
        v_array, v_index = hop.inputargs(r_array, lltype.Signed)

        inputargs = [v_array, hop.inputconst(lltype.Void, "c_data")]
        v_c_data = hop.genop('getsubstruct',
                    inputargs,
                    lltype.Ptr(r_array.lowleveltype.TO.c_data) )
        return hop.genop('getarrayitem', [v_c_data, v_index],
                r_array.r_item.lowleveltype)

def arraytype_specialize_call(hop):
    r_array = hop.r_result
    return hop.genop("malloc_varsize", [
        hop.inputconst(lltype.Void, r_array.lowleveltype.TO), 
        hop.inputconst(lltype.Signed, r_array.length),
        ], resulttype=r_array.lowleveltype,
    )

extregistry.register_type(ArrayType, 
    compute_annotation=arraytype_compute_annotation,
    specialize_call=arraytype_specialize_call)

def arraytype_get_repr(rtyper, s_array):
    return ArrayRepr(rtyper, s_array.knowntype)

extregistry.register_metatype(ArrayType, get_repr=arraytype_get_repr)
