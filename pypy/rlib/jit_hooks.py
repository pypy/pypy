
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem import llmemory, lltype
from pypy.rpython.lltypesystem import rclass
from pypy.rpython.annlowlevel import cast_instance_to_base_ptr,\
     cast_base_ptr_to_instance

def register_helper(helper, s_result):
    
    class Entry(ExtRegistryEntry):
        _about_ = helper

        def compute_result_annotation(self, *args):
            return s_result

        def specialize_call(self, hop):
            from pypy.rpython.lltypesystem import lltype

            c_func = hop.inputconst(lltype.Void, helper)
            c_name = hop.inputconst(lltype.Void, 'access_helper')
            args_v = [hop.inputarg(arg, arg=i)
                      for i, arg in enumerate(hop.args_r)]
            return hop.genop('jit_marker', [c_name, c_func] + args_v,
                             resulttype=hop.r_result)

def _cast_to_box(llref):
    from pypy.jit.metainterp.history import AbstractValue

    ptr = lltype.cast_opaque_ptr(rclass.OBJECTPTR, llref)
    return cast_base_ptr_to_instance(AbstractValue, ptr)

def _cast_to_resop(llref):
    from pypy.jit.metainterp.resoperation import AbstractResOp

    ptr = lltype.cast_opaque_ptr(rclass.OBJECTPTR, llref)
    return cast_base_ptr_to_instance(AbstractResOp, ptr)

def _cast_to_gcref(obj):
    return lltype.cast_opaque_ptr(llmemory.GCREF,
                                  cast_instance_to_base_ptr(obj))

def resop_new(no, llargs, llres):
    from pypy.jit.metainterp.history import ResOperation

    args = [_cast_to_box(llarg) for llarg in llargs]
    res = _cast_to_box(llres)
    return _cast_to_gcref(ResOperation(no, args, res))

register_helper(resop_new, annmodel.SomePtr(llmemory.GCREF))

def boxint_new(no):
    from pypy.jit.metainterp.history import BoxInt
    return _cast_to_gcref(BoxInt(no))

register_helper(boxint_new, annmodel.SomePtr(llmemory.GCREF))

def resop_opnum(llop):
    return _cast_to_resop(llop).getopnum()

register_helper(resop_opnum, annmodel.SomeInteger())
