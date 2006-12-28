from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.error import TyperError
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
            return hop.inputconst(lltype.Signed, size)
