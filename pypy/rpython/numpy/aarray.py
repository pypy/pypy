from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.tool.pairtype import pair, pairtype
from pypy.annotation.model import SomeExternalObject, SomeList, SomeImpossibleValue
from pypy.annotation.model import SomeObject, SomeInteger, SomeFloat, SomeString, SomeChar, SomeTuple, SomeSlice
from pypy.tool.error import AnnotatorError
from pypy.rpython.lltypesystem import rffi
from pypy.rlib import rarithmetic
from pypy.annotation import listdef

import numpy

numpy_typedict = {
    (SomeInteger, rffi.r_signedchar) : 'b', 
    (SomeInteger, rffi.r_short) : 'h', 
    (SomeInteger, rffi.r_int) : 'i', 
    (SomeInteger, rffi.r_long) : 'l', 
    (SomeInteger, int) : 'l', 
    (SomeInteger, rffi.r_longlong) : 'q', 
    (SomeInteger, rffi.r_uchar) : 'B', 
    (SomeInteger, rffi.r_ushort) : 'H', 
    (SomeInteger, rffi.r_uint) : 'I', 
    (SomeInteger, rffi.r_ulong) : 'L', 
    (SomeInteger, rffi.r_ulonglong) : 'Q', 
    #(SomeFloat, float) : 'f', 
    (SomeFloat, float) : 'd', 
}
valid_typecodes='bhilqBHILQd'

class SomeArray(SomeObject):
    """Stands for an object from the numpy module."""
    typecode_to_item = {
        'b' : SomeInteger(knowntype=rffi.r_signedchar),
        'h' : SomeInteger(knowntype=rffi.r_uchar),
        'i' : SomeInteger(knowntype=rffi.r_int),
        'l' : SomeInteger(knowntype=rffi.r_long),
        'q' : SomeInteger(knowntype=rffi.r_longlong),
        'B' : SomeInteger(knowntype=rffi.r_uchar),
        'H' : SomeInteger(knowntype=rffi.r_ushort),
        'I' : SomeInteger(knowntype=rffi.r_uint),
        'L' : SomeInteger(knowntype=rffi.r_ulong),
        'Q' : SomeInteger(knowntype=rffi.r_ulonglong),
        #'f' : SomeFloat(), # XX single precision float XX
        'd' : SomeFloat(),
    }

    def __init__(self, typecode, ndim=1):
        if not typecode in self.typecode_to_item:
            raise AnnotatorError("bad typecode: %r"%typecode)
        self.dtype = self.typecode = typecode
        self.ndim = ndim

    def get_one_dim(self):
        return SomeArray(self.typecode)

    def can_be_none(self):
        return True

    def get_item_type(self):
        return self.typecode_to_item[self.typecode]

    def getattr(s_array, s_attr):
        s = None
        if s_attr.is_constant() and isinstance(s_attr.const, str):
            attr = s_attr.const
            if attr == 'shape':
                s = SomeTuple([SomeInteger()]*s_array.ndim)
            elif attr == 'ndim':
                s = SomeInteger()
            elif attr == 'dtype':
                s = SomeChar()
        if s is None:
            return SomeObject.getattr(s_array, s_attr)
        return s

    def method_reshape(self, s_tuple):
        if not isinstance(s_tuple, SomeTuple):
            raise AnnotatorError("reshape expects tuple arg")
        for s_item in s_tuple.items:
            if not isinstance(s_item, SomeInteger):
                raise AnnotatorError("bad shape arg")
        ndim = len(s_tuple.items)
        return SomeArray(self.typecode, ndim)

    def method_transpose(self):
        return SomeArray(self.typecode, self.ndim)
    method_copy = method_transpose

    def method_astype(self, s_dtype):
        if isinstance(s_dtype, SomeChar) and s_dtype.is_constant():
            typecode = s_dtype.const
            return SomeArray(typecode, self.ndim)
        raise AnnotatorError()

def unify_scalar_tp(item1, item2):
    typecode = None
    if float in (item1.knowntype, item2.knowntype):
        typecode = 'd'
    else:
        item_knowntype = rarithmetic.compute_restype(item1.knowntype, item2.knowntype)
        for typecode, s_item in SomeArray.typecode_to_item.items():
            if s_item.knowntype == item_knowntype:
                break
    if typecode is None:
        raise AnnotatorError()
    return typecode

class __extend__(pairtype(SomeArray, SomeObject)):
    def add((s_arr, s_other)):
        item1 = s_arr.get_item_type()
        ndim = s_arr.ndim
        if isinstance(s_other, SomeArray):
            item2 = s_other.get_item_type()
            ndim = max(ndim, s_other.ndim)
        elif isinstance(s_other, SomeList):
            item2 = s_other.listdef.listitem.s_value
        elif isinstance(s_other, SomeFloat):
            item2 = s_other
        else:
            raise AnnotatorError("cannot operate with %s"%s_other)
        typecode = unify_scalar_tp(item1, item2)
        return SomeArray(typecode, ndim)
    sub = mul = div = add

    def inplace_add((s_arr, s_other)):
        if isinstance(s_other, SomeArray):
            # This can only work if s_other is broadcastable to s_arr
            if s_other.ndim > s_arr.ndim:
                raise AnnotatorError("invalid return array shape")
        elif isinstance(s_other, SomeList):
            item2 = s_other.listdef.listitem.s_value
            if not isinstance(item2, SomeFloat):
                raise AnnotatorError("cannot operate with list of %s"%item2)
        elif not isinstance(s_other, SomeFloat):
            raise AnnotatorError("cannot operate with %s"%s_other)
        return s_arr
    inplace_sub = inplace_mul = inplace_div = inplace_add

class __extend__(pairtype(SomeFloat, SomeArray)):
    def add((s_flt, s_arr)):
        return pair(s_arr, s_flt).add()
    sub = mul = div = add

    def inplace_add((s_flt, s_arr)):
        # This involves promoting the type of the lhs
        raise AnnotatorError()
    inplace_sub = inplace_mul = inplace_div = inplace_add

class __extend__(pairtype(SomeList, SomeArray)):
    def add((s_lst, s_arr)):
        return pair(s_arr, s_lst).add()
    sub = mul = div = add

class __extend__(pairtype(SomeArray, SomeTuple)):
    def get_leftover_dim((s_array, s_index)):
        ndim = s_array.ndim
        for s_item in s_index.items:
            if isinstance(s_item, SomeInteger):
                ndim -= 1
            elif isinstance(s_item, SomeSlice):
                pass
            else:
                raise AnnotatorError("cannot index with %s"%s_item)
        return ndim

    def setitem((s_array, s_index), s_value):
        ndim = pair(s_array, s_index).get_leftover_dim()
        if len(s_index.items)>s_array.ndim:
            raise AnnotatorError("invalid index")
        if isinstance(s_value, SomeArray):
            if s_value.ndim > ndim:
                raise AnnotatorError("shape mismatch")
        #elif ndim > 0:
        #    raise AnnotatorError("need to set from array")

    def getitem((s_array, s_index)):
        ndim = pair(s_array, s_index).get_leftover_dim()
        if len(s_index.items)>s_array.ndim:
            raise AnnotatorError("invalid index")
        if s_array.ndim == 0 and len(s_index.items):
            raise AnnotatorError("indexing rank zero array with nonempty tuple")
        if ndim > 0:
            return SomeArray(s_array.typecode, ndim)
        return s_array.get_item_type()

# These two up-cast the index to SomeTuple and call above.
class __extend__(pairtype(SomeArray, SomeSlice)):
    def setitem((s_array, s_index), s_value):
        s_tuple = SomeTuple([s_index])
        return pair(s_array, s_tuple).setitem(s_value)

    def getitem((s_array, s_index)):
        s_tuple = SomeTuple([s_index])
        return pair(s_array, s_tuple).getitem()

class __extend__(pairtype(SomeArray, SomeInteger)):
    def setitem((s_array, s_index), s_value):
        s_tuple = SomeTuple([s_index])
        return pair(s_array, s_tuple).setitem(s_value)

    def getitem((s_array, s_index)):
        s_tuple = SomeTuple([s_index])
        return pair(s_array, s_tuple).getitem()

def build_annotation_from_scalar(s_value):
    key = type(s_value), s_value.knowntype
    typecode = numpy_typedict[key]
    ndim = 1
    return SomeArray(typecode, ndim)

class ArrayCallEntry(ExtRegistryEntry):
    _about_ = numpy.array

    def compute_result_annotation(self, s_list, s_dtype=None):
        if isinstance(s_list, SomeList):
            # First guess type from input list
            listitem = s_list.listdef.listitem
            key = type(listitem.s_value), listitem.s_value.knowntype
            typecode = numpy_typedict.get(key, None)
            ndim = 1
        elif isinstance(s_list, SomeArray):
            typecode = s_list.typecode
            ndim = s_list.ndim
        else:
            raise AnnotatorError("cannot build array from %s"%s_list)

        # now see if the dtype arg over-rides the typecode
        if isinstance(s_dtype, SomeChar) and s_dtype.is_constant():
            typecode = s_dtype.const
            s_dtype = None
        if s_dtype is not None:
            raise AnnotatorError("dtype is not a valid type specification")
        if typecode is None or typecode not in valid_typecodes:
            raise AnnotatorError("List item type not supported")

        return SomeArray(typecode, ndim)

    def specialize_call(self, hop, i_dtype=None):
        r_array = hop.r_result
        v_lst = hop.inputarg(r_array, 0) # coerce list arg to array arg
        v_result = r_array.build_from_array(hop, v_lst)
        return v_result


class EmptyCallEntry(ExtRegistryEntry):
    _about_ = numpy.empty

    def compute_result_annotation(self, s_arg, s_dtype=None):
        if isinstance(s_arg, SomeTuple):
            s_tuple = s_arg
            for s_item in s_tuple.items:
                if not isinstance(s_item, SomeInteger):
                    raise AnnotatorError("shape arg not understood")
            ndim = len(s_tuple.items)
        elif isinstance(s_arg, SomeInteger):
            ndim = 1
        else:
            raise AnnotatorError("shape arg not understood: %s"%s_arg)

        typecode = 'd'
        if isinstance(s_dtype, SomeChar) and s_dtype.is_constant():
            typecode = s_dtype.const
            s_dtype = None
        return SomeArray(typecode, ndim)

    def specialize_call(self, hop, i_dtype=None):
        r_arg = hop.args_r[0]
        # XX also call with single int arg
        v_arg = hop.inputarg(r_arg, 0)
        r_array = hop.r_result
        v_result = r_array.build_from_shape(hop, r_arg, v_arg)
        return v_result

class ZerosCallEntry(EmptyCallEntry):
    _about_ = numpy.zeros

    def specialize_call(self, hop, i_dtype=None):
        r_arg = hop.args_r[0]
        # XX also call with single int arg
        v_arg = hop.inputarg(r_arg, 0)
        r_array = hop.r_result
        v_result = r_array.build_from_shape(hop, r_arg, v_arg, zero=True)
        return v_result


# Importing for side effect of registering types with extregistry
import pypy.rpython.numpy.aarray
