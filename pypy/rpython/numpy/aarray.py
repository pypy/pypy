from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.annotation.pairtype import pairtype
from pypy.annotation.model import SomeExternalObject, SomeList, SomeImpossibleValue
from pypy.annotation.model import SomeInteger, SomeFloat, SomeString, SomeChar
from pypy.annotation.listdef import ListDef
from pypy.rpython.rctypes import rcarithmetic
from pypy.tool.error import AnnotatorError

import numpy

class SomeArray(SomeExternalObject):
    """Stands for an object from the numpy module."""
    from pypy.rpython.rctypes import rcarithmetic
    typecode_to_item = {
        'b' : SomeInteger(knowntype=rcarithmetic.rcbyte),
        'h' : SomeInteger(knowntype=rcarithmetic.rcshort),
        'i' : SomeInteger(knowntype=rcarithmetic.rcint),
        'l' : SomeInteger(knowntype=rcarithmetic.rclong),
        'q' : SomeInteger(knowntype=rcarithmetic.rclonglong),
        'B' : SomeInteger(knowntype=rcarithmetic.rcubyte),
        'H' : SomeInteger(knowntype=rcarithmetic.rcushort),
        'I' : SomeInteger(knowntype=rcarithmetic.rcuint),
        'L' : SomeInteger(knowntype=rcarithmetic.rculong),
        'Q' : SomeInteger(knowntype=rcarithmetic.rculonglong),
        'f' : SomeFloat(), # XX single precision float XX
        'd' : SomeFloat(),
    }
    def __init__(self, knowntype, typecode):
        self.knowntype = knowntype
        self.typecode = typecode
        self.rank = 1

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

class __extend__(pairtype(SomeArray, SomeArray)):
    def add((s_arr1,s_arr2)):
        # TODO: coerce the array types
        return SomeArray(s_arr1.knowntype, s_arr1.typecode)

class __extend__(pairtype(SomeArray, SomeInteger)):
    def setitem((s_cto, s_index), s_value):
        pass

    def getitem((s_cto, s_index)):
        # TODO: higher ranked arrays have getitem returns SomeArray
        return s_cto.get_item_type()

numpy_typedict = {
    (SomeInteger, rcarithmetic.rcbyte) : 'b', 
    (SomeInteger, rcarithmetic.rcshort) : 'h', 
    (SomeInteger, rcarithmetic.rcint) : 'i', 
    (SomeInteger, rcarithmetic.rclong) : 'l', 
    (SomeInteger, int) : 'l', 
    (SomeInteger, rcarithmetic.rclonglong) : 'q', 
    (SomeInteger, rcarithmetic.rcubyte) : 'B', 
    (SomeInteger, rcarithmetic.rcushort) : 'H', 
    (SomeInteger, rcarithmetic.rcuint) : 'I', 
    (SomeInteger, rcarithmetic.rculong) : 'L', 
    (SomeInteger, rcarithmetic.rculonglong) : 'Q', 
    (SomeFloat, float) : 'f', 
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
        typecode = numpy_typedict.get( key, None )

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
