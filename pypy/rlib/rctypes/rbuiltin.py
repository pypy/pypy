from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.error import TyperError
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.controllerentry import SomeControlledInstance
from pypy.rlib.rctypes.implementation import getcontroller
from pypy.rlib.rctypes.implementation import register_function_impl
from pypy.rlib.rctypes import rctypesobject

import ctypes

#
# pointer()
#
register_function_impl(ctypes.pointer, rctypesobject.pointer,
                       revealargs   = [0],
                       revealresult = lambda s_obj: ctypes.POINTER(
                                                       s_obj.controller.ctype))

#
# POINTER()
#
class Entry(ExtRegistryEntry):
    "Annotation and rtyping of calls to ctypes.POINTER(): constant-folded."
    _about_ = ctypes.POINTER

    def compute_result_annotation(self, s_arg):
        # POINTER(constant_ctype) returns the constant annotation
        # corresponding to the POINTER(ctype).
        assert s_arg.is_constant(), (
            "POINTER(%r): argument must be constant" % (s_arg,))
        RESTYPE = ctypes.POINTER(s_arg.const)
            # POINTER(varsized_array_type): given that rctypes performs
            # no index checking, this pointer-to-array type is equivalent
            # to a pointer to an array of whatever size.
            # ('0' is a bad idea, though, as FixedSizeArrays of length 0
            # tend to say they have impossible items.)
            #XXX: RESTYPE = POINTER(s_arg.ctype_array._type_ * 1)
        return self.bookkeeper.immutablevalue(RESTYPE)

    def specialize_call(self, hop):
        assert hop.s_result.is_constant()
        hop.exception_cannot_occur()
        return hop.inputconst(lltype.Void, hop.s_result.const)

#
# sizeof()
#
sizeof_base_entry = register_function_impl(ctypes.sizeof, rctypesobject.sizeof,
                                           revealargs=[0], register=False)

class Entry(sizeof_base_entry):
    _about_ = ctypes.sizeof

    def compute_result_annotation(self, s_arg):
        return annmodel.SomeInteger(nonneg=True)

    def specialize_call(self, hop):
        s_arg = hop.args_s[0]
        if isinstance(s_arg, SomeControlledInstance):
            # sizeof(object)
            return sizeof_base_entry.specialize_call(self, hop)
        else:
            # sizeof(type)
            if not s_arg.is_constant():
                raise TyperError("only supports sizeof(object) or "
                                 "sizeof(constant-type)")
            ctype = s_arg.const
            sample = ctype()   # XXX can we always instantiate ctype like this?
            controller = getcontroller(ctype)
            real_obj = controller.convert(sample)
            size = rctypesobject.sizeof(real_obj)
            hop.exception_cannot_occur()
            return hop.inputconst(lltype.Signed, size)
