
from pypy.interpreter.typedef import TypeDef, interp_attrproperty
from pypy.interpreter.baseobjspace import Wrappable, ObjSpace
from pypy.interpreter.gateway import unwrap_spec, interp2app
from pypy.interpreter.pycode import PyCode
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.annlowlevel import cast_base_ptr_to_instance
from pypy.rpython.lltypesystem.rclass import OBJECT

class W_DebugMergePoint(Wrappable):
    """ A class representing debug_merge_point JIT operation
    """
    
    def __init__(self, boxes):
        self.mp_no = boxes[0].getint()
        self.offset = boxes[2].getint()
        llcode = lltype.cast_opaque_ptr(lltype.Ptr(OBJECT),
                                        boxes[4].getref_base())
        self.pycode = cast_base_ptr_to_instance(PyCode, llcode)

    @unwrap_spec('self', ObjSpace)
    def descr_repr(self, space):
        return space.wrap('DebugMergePoint()')

W_DebugMergePoint.typedef = TypeDef(
    'DebugMergePoint',
    __doc__ = W_DebugMergePoint.__doc__,
    __repr__ = interp2app(W_DebugMergePoint.descr_repr),
    code = interp_attrproperty('pycode', W_DebugMergePoint),
)

