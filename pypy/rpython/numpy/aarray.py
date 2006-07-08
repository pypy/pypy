from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.annotation.model import SomeNumpyObject, SomeList, SomeImpossibleValue
from pypy.annotation.model import SomeInteger, SomeFloat, SomeString, SomeChar
from pypy.annotation.listdef import ListDef

import numpy

numpy_knowntype = type(numpy.array([]))

numpy_typedict = {
    SomeInteger : 'i',
    SomeFloat  : 'f',
}

valid_typecodes='if'

class CallEntry(ExtRegistryEntry):
    "Annotation and rtyping of calls to numpy.array."
    _about_ = numpy.array

    def compute_result_annotation(self, arg_list, *args_s, **kwds_s):
#        print self
#        print arg_list
#        print args_s
#        print kwds_s
	if not isinstance(arg_list, SomeList):
            raise AnnotatorError("numpy.array expects SomeList")
#	if not isinstance(arg_list, SomeRange):
#            raise AnnotatorError("numpy.array expects SomeList")
        # First guess type from input list
        listtype = type(arg_list.listdef.listitem.s_value)
        
        typecode = numpy_typedict.get( listtype, None )

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
        if typecode not in valid_typecodes:
            raise AnnotatorError("List item type not supported")
        knowntype = numpy_knowntype
        print "SomeNumpyObject", knowntype, typecode
        return SomeNumpyObject(knowntype, typecode, ownsmemory=True)

    def specialize_call(self, hop):
        print "specialize_call", hop
        r_array = hop.r_result
        [v_lst] = hop.inputargs(r_array)
        v_result = r_array.allocate_instance(hop.llops, v_lst)
        return v_result

class NumpyObjEntry(ExtRegistryEntry):
    "Annotation and rtyping of numpy array instances."
    _type_ = numpy_knowntype

    def get_repr(self, rtyper, s_array):
        from pypy.rpython.numpy.rarray import ArrayRepr
        print "NumpyObjEntry.get_repr", rtyper, s_array
        return ArrayRepr(rtyper, s_array)


#class NumpyObjEntry(NumpyEntry):
#    "Annotation and rtyping of ctypes instances."
#
#    def compute_annotation(self):
#        #self.ctype_object_discovered()
#        ctype = self.type
#        return SomeNumpyObject(ctype, ownsmemory=True)


# Importing for side effect of registering types with extregistry
import pypy.rpython.numpy.aarray
