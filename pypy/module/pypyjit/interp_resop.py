
from pypy.interpreter.typedef import TypeDef, interp_attrproperty
from pypy.interpreter.baseobjspace import Wrappable, ObjSpace, W_Root
from pypy.interpreter.gateway import unwrap_spec, interp2app
from pypy.interpreter.pycode import PyCode
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.annlowlevel import cast_base_ptr_to_instance
from pypy.rpython.lltypesystem.rclass import OBJECT

class W_DebugMergePoint(Wrappable):
    """ A class representing debug_merge_point JIT operation
    """

    def __init__(self, mp_no, offset, pycode):
        self.mp_no = mp_no
        self.offset = offset
        self.pycode = pycode

    def descr_repr(self, space):
        return space.wrap('DebugMergePoint()')

@unwrap_spec(mp_no=int, offset=int, pycode=PyCode)
def new_debug_merge_point(space, w_tp, mp_no, offset, pycode):
    return W_DebugMergePoint(mp_no, offset, pycode)

def debug_merge_point_from_boxes(boxes):
    mp_no = boxes[0].getint()
    offset = boxes[2].getint()
    llcode = lltype.cast_opaque_ptr(lltype.Ptr(OBJECT),
                                    boxes[4].getref_base())
    pycode = cast_base_ptr_to_instance(PyCode, llcode)
    return W_DebugMergePoint(mp_no, offset, pycode)

W_DebugMergePoint.typedef = TypeDef(
    'DebugMergePoint',
    __new__ = interp2app(new_debug_merge_point),
    __doc__ = W_DebugMergePoint.__doc__,
    __repr__ = interp2app(W_DebugMergePoint.descr_repr),
    code = interp_attrproperty('pycode', W_DebugMergePoint),
)
