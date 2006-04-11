from ctypes import ARRAY, c_int
from pypy.annotation.model import SomeCTypesObject, SomeBuiltin
from pypy.rpython import extregistry
from pypy.rpython.rmodel import Repr, IntegerRepr, inputconst
from pypy.rpython.lltypesystem import lltype
from pypy.annotation.pairtype import pairtype
from pypy.rpython.rctypes.rmodel import CTypesRefRepr, genreccopy, reccopy

ArrayType = type(ARRAY(c_int, 10))

class ArrayRepr(CTypesRefRepr):
    def __init__(self, rtyper, s_array):
        array_ctype = s_array.knowntype
        
        item_ctype = array_ctype._type_
        self.length = array_ctype._length_
        
        # Find the repr and low-level type of items from their ctype
        self.r_item = rtyper.getrepr(SomeCTypesObject(item_ctype,
                                            SomeCTypesObject.MEMORYALIAS))

        # Here, self.c_data_type == self.ll_type
        c_data_type = lltype.FixedSizeArray(self.r_item.c_data_type,
                                            self.length)

        super(ArrayRepr, self).__init__(rtyper, s_array, c_data_type)

    def initialize_const(self, p, value):
        for i in range(self.length):
            llitem = self.r_item.convert_const(value[i])
            reccopy(llitem.c_data, p.c_data[i])

    def get_c_data_of_item(self, llops, v_array, v_index):
        v_c_array = self.get_c_data(llops, v_array)
        return llops.genop('getarraysubstruct', [v_c_array, v_index],
                           lltype.Ptr(self.r_item.c_data_type))

class __extend__(pairtype(ArrayRepr, IntegerRepr)):
    def rtype_setitem((r_array, r_int), hop):
        v_array, v_index, v_item = hop.inputargs(r_array, lltype.Signed,
                                                 r_array.r_item)
        v_item_c_data = r_array.r_item.get_c_data(hop.llops, v_item)
        v_c_data = r_array.get_c_data_of_item(hop.llops, v_array, v_index)
        # copy the whole structure's content over
        genreccopy(hop.llops, v_item_c_data, v_c_data)

    def rtype_getitem((r_array, r_int), hop):
        v_array, v_index = hop.inputargs(r_array, lltype.Signed)
        v_c_data = r_array.get_c_data_of_item(hop.llops, v_array, v_index)
        return r_array.r_item.return_c_data(hop.llops, v_c_data)


def arraytype_specialize_call(hop):
    r_array = hop.r_result
    return hop.genop("malloc", [
        hop.inputconst(lltype.Void, r_array.lowleveltype.TO), 
        ], resulttype=r_array.lowleveltype,
    )

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
    return ArrayRepr(rtyper, s_array)

extregistry.register_metatype(ArrayType,
    compute_annotation=array_instance_compute_annotation,
    get_repr=arraytype_get_repr)
