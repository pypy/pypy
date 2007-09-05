from pypy.rpython.rmodel import Repr, inputconst
from pypy.rpython.rrange import AbstractRangeRepr
from pypy.rpython.rint import IntegerRepr
from pypy.rpython.rlist import AbstractBaseListRepr
from pypy.rpython.rtuple import AbstractTupleRepr
from pypy.rpython.error import TyperError
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.rtupletype import TUPLE_TYPE
from pypy.rpython.rslice import AbstractSliceRepr
from pypy.rpython.lltypesystem.lltype import \
    GcArray, GcStruct, Signed, Ptr, Unsigned, Void, FixedSizeArray, Bool,\
    GcForwardReference, malloc, direct_arrayitems, direct_ptradd, nullptr
from pypy.rpython.lltypesystem.rtuple import TupleRepr
from pypy.annotation.model import SomeObject, SomeInteger
from pypy.rpython.numpy.aarray import SomeArray
from pypy.annotation.pairtype import pairtype, pair
from pypy.rlib.unroll import unrolling_iterable
from pypy.annotation import listdef
from pypy.rpython.memory.lltypelayout import sizeof

def gen_build_from_shape(ndim, zero=False):
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
        array.data = malloc(ARRAY.data.TO, itemsize, zero=zero)
        array.dataptr = direct_arrayitems(array.data)
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

NPY_INTP = Signed # XX index type (see Py_intptr_t)

def ARRAY_ITER(ARRAY, INDEXARRAY):
    ITER = Ptr(
        GcStruct("array_iter",
            ("nd_m1", Signed), # number of dimensions - 1 
            ("index", NPY_INTP),
            ("size", NPY_INTP),
            ("coordinates", INDEXARRAY), 
            ("dims_m1", INDEXARRAY),
            ("strides", INDEXARRAY),
            ("backstrides", INDEXARRAY),
            #("factors", INDEXARRAY),
            #("ao", ARRAY), # not needed..
            ("dataptr", ARRAY.TO.dataptr), # pointer to current item
            #("contiguous", Bool),
        ))
    return ITER

def ll_mul_list(items, n):
    result = 1
    while n:
        result *= items[n-1]
        n -= 1
    return result

def gen_iter_funcs(ndim):
    unroll_ndim = unrolling_iterable(range(ndim))
    unroll_ndim_rev = unrolling_iterable(reversed(range(ndim)))

    def ll_iter_reset(it, dataptr):
        it.index = 0
        it.dataptr = dataptr
        for i in unroll_ndim:
            it.coordinates[i] = 0
    ll_iter_reset._always_inline_ = True

    def ll_iter_new(ITER, ao, iter_reset=ll_iter_reset):
        assert ao.dataptr
        assert ao.ndim == ndim
        it = malloc(ITER)
        it.nd_m1 = ndim - 1
        it.size = ll_mul_list(ao.shape, ndim)
        #it.factors[nd-1] = 1
        for i in unroll_ndim:
            it.dims_m1[i] = ao.shape[i]-1
            it.strides[i] = ao.strides[i]
            it.backstrides[i] = it.strides[i] * it.dims_m1[i]
            #if i > 0:
                #it.factors[nd-i-1] = it.factors[nd]*ao.shape[nd-i]
        iter_reset(it, ao.dataptr)
        return it
    ll_iter_new._always_inline_ = True

    def ll_iter_broadcast_to_shape(ITER, ao, shape, iter_reset=ll_iter_reset):
        if ao.ndim > ndim:
            raise Exception("array is not broadcastable to correct shape") # XX raise here ?
        diff = j = ndim - ao.ndim
        for i in range(ao.ndim):
            if ao.shape[i] != 1 and ao.shape[i] != shape[j]:
                raise Exception("array is not broadcastable to correct shape") # XX raise here ?
            j += 1
        it = malloc(ITER)
        it.size = ll_mul_list(ao.shape, ndim)
        it.nd_m1 = ndim - 1
        #it.factors[nd-1] = 1
        for i in unroll_ndim:
            it.dims_m1[i] = ao.shape[i]-1
            k = i - diff
            if k<0 or ao.shape[k] != shape[i]:
                #it.contiguous = False
                it.strides[i] = 0
            else:
                it.strides[i] = ao.strides[k]
            it.backstrides[i] = it.strides[i] * it.dims_m1[i]
            #if i > 0:
                #it.factors[nd-i-1] = it.factors[nd-i]*shape[nd-i]
        iter_reset(it, ao.dataptr)
        return it
    ll_iter_broadcast_to_shape._always_inline_ = True    
    
    def ll_iter_next(it):
        it.index += 1
        for i in unroll_ndim_rev:
            if it.coordinates[i] < it.dims_m1[i]:
                it.coordinates[i] += 1
                it.dataptr = direct_ptradd(it.dataptr, it.strides[i])
                break
            it.coordinates[i] = 0
            it.dataptr = direct_ptradd(it.dataptr, -it.backstrides[i])
    ll_iter_next._always_inline_ = True

#    return ll_iter_new, ll_iter_broadcast_to_shape, ll_iter_next
    return ll_iter_new, ll_iter_next

def ll_unary_op(p0, p1, op=lambda x:x):
    p0[0] = op(p1[0])

def ll_binary_op(p0, p1, p2, op=lambda x,y:x+y):
    p0[0] = op(p1[0], p2[0])

def ll_array_unary_op(iter_new, iter_next, ITER, array0, array1): 
    assert array0.ndim == array1.ndim
    it0 = iter_new(ITER, array0)
    it1 = iter_new(ITER, array1)
    assert it0.size == it1.size
    while it0.index < it0.size:
        it0.dataptr[0] = it1.dataptr[0]
        iter_next(it0)
        iter_next(it1)

def dim_of_ITER(ITER):
    return ITER.TO.coordinates.length

def dim_of_ARRAY(ARRAY):
    return ARRAY.TO.shape.length

class ArrayIterRepr(Repr):
    def __init__(self, rtyper, s_iter):
        self.s_iter = s_iter
        self.lowleveltype = self.ITER

class ArrayRepr(Repr):
    def __init__(self, rtyper, s_array):
        self.s_array = s_array
        self.s_value = s_array.get_item_type()
        self.ndim = s_array.ndim
        self.item_repr = rtyper.getrepr(self.s_value) # XX rename r_item XX
        self.ITEM = self.item_repr.lowleveltype
        ITEMARRAY = GcArray(self.ITEM, hints={'nolength':True})
        self.INDEXARRAY = FixedSizeArray(NPY_INTP, self.ndim)
        self.itemsize = sizeof(self.ITEM)
        DATA_PTR = Ptr(FixedSizeArray(self.ITEM, 1))
        self.STRUCT = GcStruct("array",
            ("data", Ptr(ITEMARRAY)), # pointer to raw data buffer 
            ("dataptr", DATA_PTR), # pointer to first element
            ("ndim", Signed), # number of dimensions
            ("shape", self.INDEXARRAY), # size in each dimension
            ("strides", self.INDEXARRAY), # elements to jump to get to the
                                          # next element in each dimension 
        )
        self.ARRAY = Ptr(self.STRUCT)
        self.lowleveltype = self.ARRAY
        self.ITER = ARRAY_ITER(self.ARRAY, self.INDEXARRAY)

    def build_from_array(self, hop, v_array):
        cARRAY = inputconst(lltype.Void, self.lowleveltype.TO) 
        return hop.llops.gendirectcall(ll_build_alias, cARRAY, v_array)

    def build_from_shape(self, hop, r_arg, v_arg, zero=False):
        cARRAY = inputconst(lltype.Void, self.lowleveltype.TO) 
        ndim = self.s_array.ndim
        if isinstance(r_arg, TupleRepr):
            r_tuple, v_tuple = r_arg, v_arg
            cTUPLE = inputconst(lltype.Void, r_tuple.lowleveltype.TO)
            ll_build_from_shape = gen_build_from_shape(ndim, zero)
            c_ndim = inputconst(lltype.Signed, ndim)
            assert ndim == len(r_tuple.items_r)
            return hop.llops.gendirectcall(ll_build_from_shape, cARRAY, v_tuple)
        else:
            assert ndim == 1
            v_size = hop.inputarg(Signed, 0)
            _malloc = lambda tp, size: malloc(tp, size, zero=zero)
            cmalloc = inputconst(Void, _malloc)
            return hop.llops.gendirectcall(ll_build_from_size, cARRAY, v_size, cmalloc)

    def rtype_method_transpose(self, hop):
        [v_self] = hop.inputargs(self)
        cARRAY = hop.inputconst(Void, hop.r_result.ARRAY.TO)
        return hop.gendirectcall(ll_transpose, cARRAY, v_self)

    def get_ndim(self, hop, v_array):
        cname = inputconst(Void, 'ndim')
        return hop.llops.genop('getfield', [v_array, cname], resulttype=Signed)

    def get_shape(self, hop, v_array):
        TUPLE = TUPLE_TYPE([Signed]*self.ndim)
        cARRAY = inputconst(lltype.Void, self.lowleveltype.TO) 
        cTUPLE = inputconst(lltype.Void, TUPLE.TO)
        ll_get_shape = gen_get_shape(self.ndim)
        return hop.llops.gendirectcall(ll_get_shape, cARRAY, cTUPLE, v_array)

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
        key = self.__class__, self.typecode, self.ndim
        return key


class __extend__(pairtype(ArrayRepr, ArrayRepr)):
    def rtype_add((r_arr1, r_arr2), hop):
        v_arr1, v_arr2 = hop.inputargs(r_arr1, r_arr2)
        cARRAY = hop.inputconst(Void, hop.r_result.ARRAY.TO)
        return hop.gendirectcall(ll_add, cARRAY, v_arr1, v_arr2)


#class __extend__(pairtype(ArrayRepr, Repr)): # <------ USE THIS ??
class __extend__(pairtype(ArrayRepr, IntegerRepr)):
    def rtype_setitem((r_arr, r_int), hop):
        v_array, v_index, v_item = hop.inputargs(r_arr, Signed, r_arr.item_repr)
        return hop.gendirectcall(ll_setitem1, v_array, v_index, v_item)

    def rtype_getitem((r_arr, r_int), hop):
        v_array, v_index = hop.inputargs(r_arr, Signed)
        return hop.gendirectcall(ll_getitem1, v_array, v_index)

class __extend__(pairtype(ArrayRepr, AbstractSliceRepr)):
    def rtype_setitem((r_arr, r_slc), hop):
        r_item = hop.args_r[2]
        v_array, v_slc, v_item = hop.inputargs(r_arr, r_slc, r_item)
        cITER = hop.inputconst(Void, r_arr.ITER.TO)
        iter_new, iter_next = gen_iter_funcs(r_arr.ndim)        
        cnew = hop.inputconst(Void, iter_new)
        cnext = hop.inputconst(Void, iter_next)
        assert r_arr.ndim == r_item.ndim
        return hop.gendirectcall(ll_array_unary_op, cnew, cnext, cITER, v_array, v_item)
        
def gen_getset_item(ndim):
    unrolling_dims = unrolling_iterable(range(ndim))
    def ll_get_item(ARRAY, ao, tpl):
        array = ll_allocate(ARRAY, ndim)
        idx = 0
        for i in unrolling_dims:
            idx += ao.strides[i] * getattr(tpl, 'item%d'%i)
        return ao.data[idx]

    def ll_set_item(ARRAY, ao, tpl, value):
        array = ll_allocate(ARRAY, ndim)
        idx = 0
        for i in unrolling_dims:
            idx += ao.strides[i] * getattr(tpl, 'item%d'%i)
        ao.data[idx] = value

    return ll_get_item, ll_set_item

def get_view_ndim(r_tpl):
    return len([r_item for r_item in r_tpl.items_r if isinstance(r_item, AbstractSliceRepr)])

def gen_get_view(r_tpl):
    ndim = get_view_ndim(r_tpl)
    unroll_r_tpl = unrolling_iterable(enumerate(r_tpl.items_r))
    def ll_get_view(ARRAY, ao, tpl):
        array = ll_allocate(ARRAY, ndim)
        dataptr = direct_arrayitems(ao.data)
        src_i = 0
        tgt_i = 0
        for src_i, r_item in unroll_r_tpl:
            if isinstance(r_item, IntegerRepr):
                r_int = r_item
                dataptr = direct_ptradd(dataptr, getattr(tpl, 'item%d'%src_i)*ao.strides[src_i])
            else:
                r_slice = r_item
                array.shape[tgt_i] = ao.shape[src_i]
                array.strides[tgt_i] = ao.strides[src_i]
                tgt_i += 1
        assert tgt_i == ndim
        array.dataptr = dataptr
        array.data = ao.data # keep a ref
        return array
    return ll_get_view
            

class __extend__(pairtype(ArrayRepr, AbstractTupleRepr)):
    def rtype_getitem((r_arr, r_tpl), hop):
        v_array, v_tuple = hop.inputargs(r_arr, r_tpl)
        ndim = get_view_ndim(r_tpl)
        if ndim == 0:
            # return a scalar
            cARRAY = hop.inputconst(Void, r_arr.ARRAY.TO)
            get_item, set_item = gen_getset_item(r_arr.ndim)
            return hop.gendirectcall(get_item, cARRAY, v_array, v_tuple)
        r_result = hop.r_result
        ARRAY = r_result.ARRAY
        assert dim_of_ARRAY(ARRAY) == ndim
        cARRAY = hop.inputconst(Void, ARRAY.TO)
        ll_get_view = gen_get_view(r_tpl)
        return hop.gendirectcall(ll_get_view, cARRAY, v_array, v_tuple)

    def rtype_setitem((r_arr, r_tpl), hop):
        r_item = hop.args_r[2]
        v_array, v_tuple, v_item = hop.inputargs(r_arr, r_tpl, r_item)
        ndim = get_view_ndim(r_tpl)
        if isinstance(r_item, ArrayRepr):
            s_view = SomeArray(r_arr.s_array.typecode, ndim)
            r_view = hop.rtyper.getrepr(s_view)
            cARRAY = hop.inputconst(Void, r_view.ARRAY.TO)
            get_view = gen_get_view(r_tpl)
            v_view = hop.gendirectcall(get_view, cARRAY, v_array, v_tuple)
            iter_new, iter_next = gen_iter_funcs(ndim)        
            assert ndim == r_item.ndim
            assert dim_of_ITER(r_item.ITER) == dim_of_ITER(r_view.ITER)
            cnew = hop.inputconst(Void, iter_new)
            cnext = hop.inputconst(Void, iter_next)
            cITER = hop.inputconst(Void, r_item.ITER.TO)
            return hop.gendirectcall(ll_array_unary_op, cnew, cnext, cITER, v_view, v_item) 
        else:
            # Set from scalar
            assert ndim == 0
            cARRAY = hop.inputconst(Void, r_arr.ARRAY.TO)
            get_item, set_item = gen_getset_item(r_arr.ndim)
            return hop.gendirectcall(set_item, cARRAY, v_array, v_tuple, v_item)


class __extend__(pairtype(ArrayRepr, ArrayRepr)):
    def convert_from_to((r_arr0, r_arr1), v, llops):
        assert 0

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
    array.data = nullptr(ARRAY.data.TO)
    array.dataptr = nullptr(ARRAY.dataptr.TO)
    return array

def ll_build_from_size(ARRAY, size, _malloc):
    array = ll_allocate(ARRAY, 1)
    array.shape[0] = size
    array.strides[0] = 1
    array.data = _malloc(ARRAY.data.TO, size)
    array.dataptr = direct_arrayitems(array.data)
    return array

def ll_build_from_list(ARRAY, lst):
    size = lst.ll_length()
    array = ll_allocate(ARRAY, 1)
    array.shape[0] = size
    array.strides[0] = 1
    array.data = malloc(ARRAY.data.TO, size)
    i = 0
    while i < size:
        array.data[i] = lst.ll_getitem_fast(i)
        i += 1
    array.dataptr = direct_arrayitems(array.data)
    return array

def ll_build_alias(ARRAY, ao):
    array = ll_allocate(ARRAY, ao.ndim)
    array.data = ao.data # alias data
    for i in range(ao.ndim):
        array.shape[i] = ao.shape[i]
        array.strides[i] = ao.strides[i]
    array.dataptr = ao.dataptr
    return array

def ll_setitem1(l, index, item):
    l.data[index] = item

def ll_getitem1(l, index):
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
    array.dataptr = direct_arrayitems(array.data)
    return array

def ll_transpose(ARRAY, a1):
    a2 = ll_build_alias(ARRAY, a1)
    # XX do something to a2
    return a2
    


