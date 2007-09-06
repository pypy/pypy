from pypy.rpython.rmodel import Repr, FloatRepr, inputconst
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

def gen_build_alias_shape(ndim):
    unrolling_dims = unrolling_iterable(reversed(range(ndim)))
    def ll_build_alias_shape(ARRAY, ao, shape):
        array = ll_allocate(ARRAY, ndim)
        itemsize = 1
        for i in unrolling_dims:
            attr = 'item%d'%i
            size = getattr(shape, attr)
            array.shape[i] = size
            array.strides[i] = itemsize
            itemsize *= size
        array.data = ao.data
        array.dataptr = ao.dataptr
        return array
    return ll_build_alias_shape

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
            ("dims_m1", INDEXARRAY), # array of dimensions - 1
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

    def ll_iter_broadcast_to_shape(ITER, ao, target_ao, iter_reset=ll_iter_reset):
        "iterate over <ao> but broadcast to the shape of <target_ao>"
        assert target_ao.ndim == ndim
        delta = j = ndim - ao.ndim
        shape = target_ao.shape
        for i in range(ao.ndim):
            if ao.shape[i] != 1 and ao.shape[i] != shape[j]:
                raise Exception("array is not broadcastable to correct shape")
            j += 1
        it = malloc(ITER)
        it.size = ll_mul_list(target_ao.shape, ndim)
        it.nd_m1 = ndim - 1
        #it.factors[ndim-1] = 1
        for i in unroll_ndim:
            it.dims_m1[i] = shape[i]-1
            k = i - delta
            if k<0 or ao.shape[k] != shape[i]:
                #it.contiguous = False
                it.strides[i] = 0
            else:
                it.strides[i] = ao.strides[k]
            it.backstrides[i] = it.strides[i] * it.dims_m1[i]
            #if i > 0:
                #it.factors[ndim-i-1] = it.factors[nd-i]*shape[ndim-i]
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

    return ll_iter_new, ll_iter_reset, ll_iter_broadcast_to_shape, ll_iter_next

def ll_unary_op(p0, p1, op=lambda x:x):
    p0[0] = op(p1[0])

def ll_binary_op(p0, p1, p2, op=lambda x,y:x+y):
    p0[0] = op(p1[0], p2[0])


def ll_array_set(it0, it1, iter_next):
    assert it0.size == it1.size
    while it0.index < it0.size:
        it0.dataptr[0] = it1.dataptr[0]
        iter_next(it0)
        iter_next(it1)

def ll_array_set1(value, it, iter_next):
    while it.index < it.size:
        it.dataptr[0] = value
        iter_next(it)

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

    def rtype_method_reshape(self, hop):
        r_result = hop.r_result
        r_tuple = hop.args_r[1]
        if not isinstance(r_tuple, TupleRepr):
            raise TyperError()
        ndim = len(r_tuple.items_r)
        ll_build_alias_shape = gen_build_alias_shape(ndim)
        [v_array, v_tuple] = hop.inputargs(self, r_tuple)
        cARRAY = inputconst(lltype.Void, r_result.lowleveltype.TO) 
        return hop.llops.gendirectcall(ll_build_alias_shape, cARRAY, v_array, v_tuple)

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
    def rtype_add((r_array1, r_array2), hop):
        v_arr1, v_arr2 = hop.inputargs(r_array1, r_array2)
        cARRAY = hop.inputconst(Void, hop.r_result.ARRAY.TO)
        return hop.gendirectcall(ll_add, cARRAY, v_arr1, v_arr2)


#class __extend__(pairtype(ArrayRepr, Repr)): # <------ USE THIS ??
class __extend__(pairtype(ArrayRepr, IntegerRepr)):
    def rtype_setitem((r_array, r_int), hop):
        assert r_array.ndim == 1, "NotImplemented"
        v_array, v_index, v_item = hop.inputargs(r_array, Signed, r_array.item_repr)
        return hop.gendirectcall(ll_setitem1, v_array, v_index, v_item)

    def rtype_getitem((r_array, r_int), hop):
        assert r_array.ndim == 1, "NotImplemented"
        v_array, v_index = hop.inputargs(r_array, Signed)
        return hop.gendirectcall(ll_getitem1, v_array, v_index)

def gen_get_view_slc(r_array, r_slc, hop): # XX method on the pair type ?
    ndim = r_array.ndim
    rslice = hop.rtyper.type_system.rslice
    def ll_get_view_slc(ARRAY, ao, slc):
        array = ll_allocate(ARRAY, ndim)
        dataptr = direct_arrayitems(ao.data)
        src_i = 0
        tgt_i = 0
        if r_slc == rslice.startonly_slice_repr:
            start = slc
            size = ao.shape[src_i]
            if start > size:
                start = size
            size -= start
            dataptr = direct_ptradd(dataptr, start*ao.strides[src_i])
            array.shape[tgt_i] = size
            array.strides[tgt_i] = ao.strides[src_i]
            tgt_i += 1
        elif r_slc == rslice.startstop_slice_repr:
            start = slc.start
            stop = slc.stop
            size = ao.shape[src_i]
            if start > size:
                start = size
            dataptr = direct_ptradd(dataptr, start*ao.strides[src_i])
            if stop < size:
                size = stop
            size -= start
            if size < 0:
                size = 0
            array.shape[tgt_i] = size
            array.strides[tgt_i] = ao.strides[src_i]
            tgt_i += 1
        else:
            assert 0
        src_i += 1
        # consume the rest of ndim as if we found more slices
        while tgt_i < ndim:
            array.shape[tgt_i] = ao.shape[src_i]
            array.strides[tgt_i] = ao.strides[src_i]
            tgt_i += 1
            src_i += 1
        assert tgt_i == ndim
        array.dataptr = dataptr
        array.data = ao.data # keep a ref
        return array
    return ll_get_view_slc
            
class __extend__(pairtype(ArrayRepr, AbstractSliceRepr)):
    def rtype_setitem((r_array, r_slc), hop):
        r_item = hop.args_r[2]
        v_array, v_slc, v_item = hop.inputargs(r_array, r_slc, r_item)
        cITER = hop.inputconst(Void, r_array.ITER.TO)
        cARRAY = hop.inputconst(Void, r_array.ARRAY.TO)
        iter_new, iter_reset, iter_broadcast, iter_next = gen_iter_funcs(r_array.ndim)        
        cnext = hop.inputconst(Void, iter_next)
        creset = hop.inputconst(Void, iter_reset)
## Blech... it would be nice to reuse gen_get_view
##            r_tuple = TupleRepr(hop.rtyper, [r_item]) # XX how to get this from rtyper ?
##            get_view = gen_get_view(r_array, r_tuple, hop)
##            # make a v_tuple here... 
##            v_view = hop.gendirectcall(get_view, cARRAY, v_array, v_tuple)
        get_view = gen_get_view_slc(r_array, r_slc, hop)
        v_view = hop.gendirectcall(get_view, cARRAY, v_array, v_slc)
        v_it0 = hop.gendirectcall(iter_new, cITER, v_view, creset)
        if isinstance(r_item, ArrayRepr):
            if r_array.ndim == r_item.ndim:
                v_it1 = hop.gendirectcall(iter_new, cITER, v_item, creset)
            else:
                v_it1 = hop.gendirectcall(iter_broadcast, cITER, v_item, v_array, creset)
            assert r_array.ndim >= r_item.ndim
            return hop.gendirectcall(ll_array_set, v_it0, v_it1, cnext)
        elif isinstance(r_item, FloatRepr):
            # setitem from scalar
            return hop.gendirectcall(ll_array_set1, v_item, v_it0, cnext)
        else:
            raise TypeError("can't setitem from %s"%r_item)
        
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

def get_view_ndim(r_array, r_tuple): # XX method on the pair type ?
    ndim = len([r_item for r_item in r_tuple.items_r if isinstance(r_item, AbstractSliceRepr)])
    ndim += r_array.ndim - len(r_tuple.items_r)
    return ndim

def gen_get_view(r_array, r_tuple, hop): # XX method on the pair type ?
    ndim = get_view_ndim(r_array, r_tuple)
    unroll_r_tuple = unrolling_iterable(enumerate(r_tuple.items_r))
    rslice = hop.rtyper.type_system.rslice
    def ll_get_view(ARRAY, ao, tpl):
        array = ll_allocate(ARRAY, ndim)
        dataptr = direct_arrayitems(ao.data)
        src_i = 0
        tgt_i = 0
        for src_i, r_key in unroll_r_tuple:
            if isinstance(r_key, IntegerRepr):
                dataptr = direct_ptradd(dataptr, getattr(tpl, 'item%d'%src_i)*ao.strides[src_i])
            elif r_key == rslice.startonly_slice_repr:
                start = getattr(tpl, 'item%d'%src_i)
                size = ao.shape[src_i]
                if start > size:
                    start = size
                size -= start
                dataptr = direct_ptradd(dataptr, start*ao.strides[src_i])
                array.shape[tgt_i] = size
                array.strides[tgt_i] = ao.strides[src_i]
                tgt_i += 1
            elif r_key == rslice.startstop_slice_repr:
                start = getattr(tpl, 'item%d'%src_i).start
                stop = getattr(tpl, 'item%d'%src_i).stop
                size = ao.shape[src_i]
                if start > size:
                    start = size
                dataptr = direct_ptradd(dataptr, start*ao.strides[src_i])
                if stop < size:
                    size = stop
                size -= start
                if size < 0:
                    size = 0
                array.shape[tgt_i] = size
                array.strides[tgt_i] = ao.strides[src_i]
                tgt_i += 1
            else:
                assert 0
        src_i += 1
        # consume the rest of ndim as if we found more slices
        while tgt_i < ndim:
            array.shape[tgt_i] = ao.shape[src_i]
            array.strides[tgt_i] = ao.strides[src_i]
            tgt_i += 1
            src_i += 1
        assert tgt_i == ndim
        array.dataptr = dataptr
        array.data = ao.data # keep a ref
        return array
    return ll_get_view
            

class __extend__(pairtype(ArrayRepr, AbstractTupleRepr)):
    def rtype_getitem((r_array, r_tpl), hop):
        v_array, v_tuple = hop.inputargs(r_array, r_tpl)
        ndim = get_view_ndim(r_array, r_tpl)
        if ndim == 0:
            # return a scalar
            cARRAY = hop.inputconst(Void, r_array.ARRAY.TO)
            get_item, set_item = gen_getset_item(r_array.ndim)
            return hop.gendirectcall(get_item, cARRAY, v_array, v_tuple)
        r_result = hop.r_result
        ARRAY = r_result.ARRAY
        assert dim_of_ARRAY(ARRAY) == ndim
        cARRAY = hop.inputconst(Void, ARRAY.TO)
        ll_get_view = gen_get_view(r_array, r_tpl, hop)
        return hop.gendirectcall(ll_get_view, cARRAY, v_array, v_tuple)

    def rtype_setitem((r_array, r_tuple), hop):
        r_item = hop.args_r[2]
        v_array, v_tuple, v_item = hop.inputargs(r_array, r_tuple, r_item)
        ndim = get_view_ndim(r_array, r_tuple)
        assert len(r_tuple.items_r) <= r_array.ndim
        if ndim == 0:
            # Set from scalar
            assert isinstance(r_item, FloatRepr)
            cARRAY = hop.inputconst(Void, r_array.ARRAY.TO)
            get_item, set_item = gen_getset_item(r_array.ndim)
            return hop.gendirectcall(set_item, cARRAY, v_array, v_tuple, v_item)
        elif isinstance(r_item, ArrayRepr):
            s_view = SomeArray(r_array.s_array.typecode, ndim)
            r_view = hop.rtyper.getrepr(s_view)
            cARRAY = hop.inputconst(Void, r_view.ARRAY.TO)
            get_view = gen_get_view(r_array, r_tuple, hop)
            v_view = hop.gendirectcall(get_view, cARRAY, v_array, v_tuple)
            iter_new, iter_reset, iter_broadcast, iter_next = gen_iter_funcs(ndim)        
            creset = hop.inputconst(Void, iter_reset)
            cnext = hop.inputconst(Void, iter_next)
            cITER = hop.inputconst(Void, r_view.ITER.TO)
            v_it0 = hop.gendirectcall(iter_new, cITER, v_view, creset)
            assert r_item.ndim <= ndim
            if ndim == r_item.ndim:
                v_it1 = hop.gendirectcall(iter_new, cITER, v_item, creset)
            else:
                v_it1 = hop.gendirectcall(iter_broadcast, cITER, v_item, v_view, creset)
            return hop.gendirectcall(ll_array_set, v_it0, v_it1, cnext) 
        else:
            assert 0


class __extend__(pairtype(ArrayRepr, ArrayRepr)):
    def convert_from_to((r_array0, r_array1), v, llops):
        assert 0

class __extend__(pairtype(AbstractBaseListRepr, ArrayRepr)):
    def convert_from_to((r_lst, r_array), v, llops):
        if r_lst.listitem is None:
            return NotImplemented
        if r_lst.item_repr != r_array.item_repr:
            assert 0, (r_lst, r_array.item_repr)
            return NotImplemented
        cARRAY = inputconst(lltype.Void, r_array.lowleveltype.TO) 
        return llops.gendirectcall(ll_build_from_list, cARRAY, v)

class __extend__(pairtype(AbstractRangeRepr, ArrayRepr)):
    def convert_from_to((r_rng, r_array), v, llops):
        cARRAY = inputconst(lltype.Void, r_array.lowleveltype.TO) 
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

def ll_transpose(ARRAY, ao):
    ndim = ao.ndim
    array = ll_allocate(ARRAY, ndim)
    array.data = ao.data # alias data
    for i in range(ndim):
        array.shape[i] = ao.shape[ndim-i-1]
        array.strides[i] = ao.strides[ndim-i-1]
    array.dataptr = ao.dataptr
    return array
    


