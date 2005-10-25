from pypy.rpython import rstack, lltype, extfunctable
from pypy.rpython.module.support import from_opaque_object, to_opaque_object

FRAMETOPTYPE = extfunctable.frametop_type_info.get_lltype()


def ll_stackless_stack_frames_depth():
    return rstack.stack_frames_depth()
ll_stackless_stack_frames_depth.suggested_primitive = True


def ll_stackless_switch(opaqueframetop):
    frametop = from_opaque_object(opaqueframetop)
    newframetop = frametop.switch()
    if newframetop is None:
        return lltype.nullptr(FRAMETOPTYPE)
    else:
        return to_opaque_object(newframetop)
ll_stackless_switch.suggested_primitive = True
