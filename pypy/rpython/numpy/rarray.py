from pypy.rpython.rmodel import Repr, inputconst
from pypy.rpython.rrange import AbstractRangeRepr
from pypy.rpython.rint import IntegerRepr
from pypy.rpython.rlist import AbstractBaseListRepr
from pypy.rpython.error import TyperError
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.rtupletype import TUPLE_TYPE
from pypy.rpython.lltypesystem.lltype import \
     GcArray, GcStruct, Signed, Ptr, Unsigned, malloc, Void
from pypy.annotation.model import SomeObject, SomeInteger
from pypy.rpython.numpy.aarray import SomeArray
from pypy.annotation.pairtype import pairtype
from pypy.rlib.unroll import unrolling_iterable
from pypy.annotation import listdef
from pypy.rpython.memory.lltypelayout import sizeof

def gen_build_from_shape(ndim):
    unrolling_dims = unrolling_iterable(reversed(range(ndim)))
    def ll_build_from_shape(ARRAY, shape):
        array = ll_allocate(ARRAY, ndim)
        itemsize = 1
        for i in unrolling_dims:
            attr = 'item%d'%i
            size = getattr(shape, attr)
            array.shape[i] = size
            array.strides[i] = itemsize
            itemsize *= size
        array.data = malloc(ARRAY.data.TO, itemsize)
        return array
    return ll_build_from_shape

def gen_get_shape(ndim):
    unrolling_dims = unrolling_iterable(range(ndim))
    def ll_get_shape(ARRAY, TUPLE, array):
        shape = malloc(TUPLE)
        for i in unrolling_dims:
            size = array.shape[i]
            attr = 'item%d'%i
            setattr(shape, attr, size)
        return shape
    return ll_get_shape


class ArrayRepr(Repr):
    def __init__(self, rtyper, s_array):
        self.s_array = s_array
        self.s_value = s_array.get_item_type()
        self.item_repr = rtyper.getrepr(self.s_value)
        ITEM = self.item_repr.lowleveltype
        ITEMARRAY = GcArray(ITEM, hints={'nolength':True})
        SIZEARRAY = GcArray(Signed, hints={'nolength':True})
        self.PTR_SIZEARRAY = Ptr(SIZEARRAY)
        self.itemsize = sizeof(ITEM)
        self.ndim = s_array.ndim
        self.ARRAY = Ptr(
            GcStruct("array",
                ("data", Ptr(ITEMARRAY)), # pointer to raw data buffer 
                ("ndim", Signed), # number of dimensions
                ("shape", self.PTR_SIZEARRAY), # size in each dimension
                ("strides", self.PTR_SIZEARRAY), # bytes (?) to jump to get to the
                                                 # next element in each dimension 
            ))
        self.lowleveltype = self.ARRAY

    def build_from_array(self, llops, v_array):
        cARRAY = inputconst(lltype.Void, self.lowleveltype.TO) 
        return llops.gendirectcall(ll_build_alias, cARRAY, v_array)

#    def build_from_shape(self, llops, r_tuple, v_tuple):
#        cARRAY = inputconst(lltype.Void, self.lowleveltype.TO) 
#        cTUPLE = inputconst(lltype.Void, r_tuple.lowleveltype.TO)
#        ndim = self.ndim
#        c_ndim = inputconst(lltype.Signed, ndim)
#        assert ndim == len(r_tuple.items_r)
#        v_array = llops.gendirectcall(ll_allocate, cARRAY, c_ndim)
#        c_attr = inputconst(lltype.Void, 'shape')
#        v_shape = llops.genop('getfield', [v_array, c_attr], self.PTR_SIZEARRAY)
#        for i in range(ndim):
#            v_size = r_tuple.getitem_internal(llops, v_tuple, i)
#            v_i = inputconst(lltype.Signed, i)
#            llops.genop('setarrayitem', [v_shape, v_i, v_size])
#        return v_array
        
    def build_from_shape(self, llops, r_tuple, v_tuple):
        cARRAY = inputconst(lltype.Void, self.lowleveltype.TO) 
        cTUPLE = inputconst(lltype.Void, r_tuple.lowleveltype.TO)
        ndim = self.s_array.ndim
        ll_build_from_shape = gen_build_from_shape(ndim)
        c_ndim = inputconst(lltype.Signed, ndim)
        assert ndim == len(r_tuple.items_r)
        rval = llops.gendirectcall(ll_build_from_shape, cARRAY, v_tuple)
        return rval

    def rtype_method_transpose(self, hop):
        [v_self] = hop.inputargs(self)
        cARRAY = hop.inputconst(Void, hop.r_result.ARRAY.TO)
        return hop.gendirectcall(ll_transpose, cARRAY, v_self)

    def get_ndim(self, hop, v_array):
        cname = inputconst(Void, 'ndim')
        return hop.llops.genop('getfield', [v_array, cname], resulttype=Signed)

    def get_shape(self, hop, v_array):
        cname = inputconst(Void, 'shape')
        TUPLE = TUPLE_TYPE([Signed]*self.ndim)
        cARRAY = inputconst(lltype.Void, self.lowleveltype.TO) 
        cTUPLE = inputconst(lltype.Void, TUPLE.TO)
        ll_get_shape = gen_get_shape(self.ndim)
        return hop.llops.gendirectcall(ll_get_shape, cARRAY, cTUPLE, v_array)
        return llops.genop('getfield', [v_array, cname], resulttype=TUPLE)

    def rtype_getattr(self, hop):
        s_attr = hop.args_s[1]
        if s_attr.is_constant() and isinstance(s_attr.const, str):
            attr = s_attr.const
            s_obj = hop.args_s[0]
            v_array, vattr = hop.inputargs(self, Void)
            getter = getattr(self, 'get_'+attr, None)
            if getter:
                return getter(hop, v_array)
        return Repr.rtype_getattr(self, hop)


class __extend__(SomeArray):
    def rtyper_makerepr(self, rtyper):
        return ArrayRepr(rtyper, self)

    def rtyper_makekey(self):
        return self.__class__, self.typecode, self.ndim


class __extend__(pairtype(ArrayRepr, ArrayRepr)):
    def rtype_add((r_arr1,r_arr2), hop):
        v_arr1, v_arr2 = hop.inputargs(r_arr1, r_arr2)
        cARRAY = hop.inputconst(Void, hop.r_result.ARRAY.TO)
        return hop.gendirectcall(ll_add, cARRAY, v_arr1, v_arr2)


class __extend__(pairtype(ArrayRepr, IntegerRepr)):
    def rtype_setitem((r_arr,r_int), hop):
        v_array, v_index, v_item = hop.inputargs(r_arr, Signed, r_arr.item_repr)
        return hop.gendirectcall(ll_setitem, v_array, v_index, v_item)

    def rtype_getitem((r_arr,r_int), hop):
        v_array, v_index = hop.inputargs(r_arr, Signed)
        return hop.gendirectcall(ll_getitem, v_array, v_index)

class __extend__(pairtype(AbstractBaseListRepr, ArrayRepr)):
    def convert_from_to((r_lst, r_arr), v, llops):
        if r_lst.listitem is None:
            return NotImplemented
        if r_lst.item_repr != r_arr.item_repr:
            assert 0, (r_lst, r_arr.item_repr)
            return NotImplemented
        cARRAY = inputconst(lltype.Void, r_arr.lowleveltype.TO) 
        return llops.gendirectcall(ll_build_from_list, cARRAY, v)

class __extend__(pairtype(AbstractRangeRepr, ArrayRepr)):
    def convert_from_to((r_rng, r_arr), v, llops):
        cARRAY = inputconst(lltype.Void, r_arr.lowleveltype.TO) 
        return llops.gendirectcall(ll_build_from_list, cARRAY, v)

def ll_allocate(ARRAY, ndim):
    array = malloc(ARRAY)
    array.ndim = ndim
    array.shape = malloc(ARRAY.shape.TO, array.ndim)
    array.strides = malloc(ARRAY.strides.TO, array.ndim)
    return array

def ll_build_from_list(ARRAY, lst):
    size = lst.ll_length()
    array = ll_allocate(ARRAY, 1)
    for i in range(array.ndim):
        array.shape[i] = size
        array.strides[i] = 1
    data = array.data = malloc(ARRAY.data.TO, size)
    i = 0
    while i < size:
        data[i] = lst.ll_getitem_fast(i)
        i += 1
    return array

def ll_build_alias(ARRAY, array):
    new_array = ll_allocate(ARRAY, array.ndim)
    new_array.data = array.data # alias data
    for i in range(array.ndim):
        new_array.shape[i] = array.shape[i]
        new_array.strides[i] = array.strides[i]
    return new_array

def ll_setitem(l, index, item):
    l.data[index] = item

def ll_getitem(l, index):
    return l.data[index]

def ll_add(ARRAY, a1, a2):
    size = a1.shape[0]
    if size != a2.shape[0]:
        raise ValueError
    array = malloc(ARRAY)
    array.data = malloc(ARRAY.data.TO, size)
    i = 0
    while i < size:
        array.data[i] = a1.data[i] + a2.data[i]
        i += 1
    return array

def ll_transpose(ARRAY, a1):
    a2 = ll_build_alias(ARRAY, a1)
    # XX do something to a2
    return a2
    


