from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.annotation.model import SomeNumpyObject, SomeList, SomeImpossibleValue
from pypy.annotation.model import SomeInteger, SomeFloat, SomeString, SomeChar

import numpy

numpy_typedict = {
    SomeInteger : 'i',
    SomeFloat  : 'f',
}

valid_typecodes='if'

class CallEntry(ExtRegistryEntry):
    "Annotation and rtyping of calls to numpy.array."
    _about_ = numpy.array

    def compute_result_annotation(self, arg_list, *args_s, **kwds_s):
        print self
        print arg_list
        print args_s
        print kwds_s
	if not isinstance(arg_list, SomeList):
            raise AnnotatorError("ahh!!")
        # First guess type from input list
        listtype = type(arg_list.listdef.listitem.s_value)
        
        typecode = numpy_typedict.get( listtype , None )

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
        ctype = self.instance    # the ctype is the called object
        return SomeNumpyObject(ctype, typecode, ownsmemory=True)

    def specialize_call(self, hop):
        r_void_p = hop.r_result
        hop.exception_cannot_occur()
        v_result = r_void_p.allocate_instance(hop.llops)
        return v_result

class NumpyObjEntry(ExtRegistryEntry):
    "Annotation and rtyping of XX instances."
    _type_ = type(numpy.array([]))

    def get_repr(self, rtyper, s_void_p):
        # XX FIX
        from pypy.rpython.rctypes.rvoid_p import CVoidPRepr
        from pypy.rpython.lltypesystem import llmemory
        return CVoidPRepr(rtyper, s_void_p, llmemory.Address)


#class NumpyObjEntry(NumpyEntry):
#    "Annotation and rtyping of ctypes instances."
#
#    def compute_annotation(self):
#        #self.ctype_object_discovered()
#        ctype = self.type
#        return SomeNumpyObject(ctype, ownsmemory=True)


# Importing for side effect of registering types with extregistry
import pypy.rpython.numpy.aarray
