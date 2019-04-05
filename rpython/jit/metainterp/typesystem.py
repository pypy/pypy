from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.rtyper import rclass
from rpython.jit.metainterp import history
from rpython.jit.metainterp.support import ptr2int
from rpython.rlib.objectmodel import r_dict


class TypeSystemHelper(object):

    def _freeze_(self):
        return True

class LLTypeHelper(TypeSystemHelper):

    name = 'lltype'

    def cls_of_box(self, box):
        obj = lltype.cast_opaque_ptr(rclass.OBJECTPTR, box.getref_base())
        return history.ConstInt(ptr2int(obj.typeptr))

llhelper = LLTypeHelper()
