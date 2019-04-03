from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.rtyper import rclass
from rpython.jit.metainterp import history
from rpython.jit.codewriter import heaptracker
from rpython.rlib.objectmodel import r_dict


class TypeSystemHelper(object):

    def _freeze_(self):
        return True

class LLTypeHelper(TypeSystemHelper):

    name = 'lltype'

    def cls_of_box(self, box):
        obj = lltype.cast_opaque_ptr(rclass.OBJECTPTR, box.getref_base())
        cls = llmemory.cast_ptr_to_adr(obj.typeptr)
        return history.ConstInt(heaptracker.adr2int(cls))

llhelper = LLTypeHelper()
