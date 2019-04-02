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

    # A dict whose keys are refs (like the .value of BoxPtr).
    # It is an r_dict on lltype.  Two copies, to avoid conflicts with
    # the value type.  Note that NULL is not allowed as a key.
    def new_ref_dict(self):
        return r_dict(rd_eq, rd_hash, simple_hash_eq=True)

    def new_ref_dict_2(self):
        return r_dict(rd_eq, rd_hash, simple_hash_eq=True)

    def new_ref_dict_3(self):
        return r_dict(rd_eq, rd_hash, simple_hash_eq=True)

def rd_eq(ref1, ref2):
    return ref1 == ref2

def rd_hash(ref):
    assert ref
    return lltype.identityhash(ref)

llhelper = LLTypeHelper()
