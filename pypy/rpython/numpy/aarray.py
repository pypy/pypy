from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.annotation.pairtype import pairtype
from pypy.annotation.model import SomeExternalObject, SomeList, SomeImpossibleValue
from pypy.annotation.model import SomeObject, SomeInteger, SomeFloat, SomeString, SomeChar,\
    SomeGenericCallable
from pypy.tool.error import AnnotatorError
from pypy.rpython.lltypesystem import rffi
from pypy.rlib import rarithmetic

import numpy

class SomeArray(SomeExternalObject):
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
    def __init__(self, knowntype, typecode, rank=1):
        self.knowntype = knowntype # == numpy.ndarray (do we need this for anything?)
        self.typecode = typecode
        self.rank = rank

    def can_be_none(self):
        return True

    def return_annotation(self):
        """Returns either 'self' or the annotation of the unwrapped version
        of this ctype, following the logic used when ctypes operations
        return a value.
        """
        from pypy.rpython import extregistry
        assert extregistry.is_registered_type(self.knowntype)
        entry = extregistry.lookup_type(self.knowntype)
        # special case for returning primitives or c_char_p
        return getattr(entry, 's_return_trick', self)

    def get_item_type(self):
        return self.typecode_to_item[self.typecode]

    def getattr(s_array, s_attr):
        s = None
        if s_attr.is_constant() and isinstance(s_attr.const, str):
            attr = s_attr.const
            if attr in ('transpose',):
                s_result = SomeArray(s_array.knowntype, s_array.typecode, s_array.rank)
                s = SomeGenericCallable([], s_result)
            elif attr == 'shape':
                s = SomeTuple([SomeInteger()]*s_array.rank)
        if s is None:
            return SomeObject()
        return s

class __extend__(pairtype(SomeArray, SomeArray)):

    def union((s_arr1, s_arr2)):
        item1 = s_arr1.get_item_type()
        item2 = s_arr2.get_item_type()
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
        return SomeArray(s_arr1.knowntype, typecode)

    add = sub = mul = div = truediv = union


class __extend__(pairtype(SomeArray, SomeInteger)):
    def setitem((s_cto, s_index), s_value):
        pass

    def getitem((s_cto, s_index)):
        # TODO: higher ranked arrays have getitem returns SomeArray
        return s_cto.get_item_type()

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
valid_typecodes='bhilqBHILQfd'

class CallEntry(ExtRegistryEntry):
    "Annotation and rtyping of calls to numpy.array."
    _about_ = numpy.array

    def compute_result_annotation(self, arg_list, *args_s, **kwds_s):
        if not isinstance(arg_list, SomeList):
            raise AnnotatorError("numpy.array expects SomeList")

        # First guess type from input list
        listitem = arg_list.listdef.listitem
        key = type(listitem.s_value), listitem.s_value.knowntype
        typecode = numpy_typedict.get(key, None)

        # now see if the dtype arg over-rides the typecode
        dtype = None
        if len(args_s)>0:
            dtype = args_s[0]
        if "dtype" in kwds_s:
            dtype = kwds_s["dtype"]
        if isinstance(dtype,SomeChar) and dtype.is_constant():
            typecode = dtype.const
            dtype = None
        if dtype is not None:
            raise AnnotatorError("dtype is not a valid type specification")
        if typecode is None or typecode not in valid_typecodes:
            raise AnnotatorError("List item type not supported")
        knowntype = numpy.ndarray
        return SomeArray(knowntype, typecode)

    def specialize_call(self, hop):
        r_array = hop.r_result
        [v_lst] = hop.inputargs(r_array)
        v_result = r_array.allocate_instance(hop.llops, v_lst)
        return v_result

class NumpyObjEntry(ExtRegistryEntry):
    "Annotation and rtyping of numpy array instances."
    _type_ = numpy.ndarray

    def get_repr(self, rtyper, s_array):
        from pypy.rpython.numpy.rarray import ArrayRepr
        return ArrayRepr(rtyper, s_array)



# Importing for side effect of registering types with extregistry
import pypy.rpython.numpy.aarray
