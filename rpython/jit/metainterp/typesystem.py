from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.rtyper import rclass
from rpython.rtyper.annlowlevel import cast_base_ptr_to_instance, llstr
from rpython.jit.metainterp import history
from rpython.jit.codewriter import heaptracker
from rpython.rlib.objectmodel import r_dict, specialize

def deref(T):
    assert isinstance(T, lltype.Ptr)
    return T.TO


def fieldType(T, name):
    assert isinstance(T, lltype.Struct)
    return getattr(T, name)

def arrayItem(ARRAY):
    try:
        return ARRAY.OF
    except AttributeError:
        return ARRAY.ITEM

class TypeSystemHelper(object):

    def _freeze_(self):
        return True

class LLTypeHelper(TypeSystemHelper):

    name = 'lltype'

    def cls_of_box(self, box):
        obj = lltype.cast_opaque_ptr(rclass.OBJECTPTR, box.getref_base())
        cls = llmemory.cast_ptr_to_adr(obj.typeptr)
        return history.ConstInt(heaptracker.adr2int(cls))

    def instanceOf(self, instbox, clsbox):
        adr = clsbox.getaddr()
        bounding_class = llmemory.cast_adr_to_ptr(adr, rclass.CLASSTYPE)
        real_instance = instbox.getref(rclass.OBJECTPTR)
        return rclass.ll_isinstance(real_instance, bounding_class)

    def get_exception_box(self, etype):
        return history.ConstInt(etype)

    def get_exception_obj(self, evaluebox):
        # only works when translated
        obj = evaluebox.getref(rclass.OBJECTPTR)
        return cast_base_ptr_to_instance(Exception, obj)

    # A dict whose keys are refs (like the .value of BoxPtr).
    # It is an r_dict on lltype.  Two copies, to avoid conflicts with
    # the value type.  Note that NULL is not allowed as a key.
    def new_ref_dict(self):
        return r_dict(rd_eq, rd_hash, simple_hash_eq=True)

    def new_ref_dict_2(self):
        return r_dict(rd_eq, rd_hash, simple_hash_eq=True)

    def new_ref_dict_3(self):
        return r_dict(rd_eq, rd_hash, simple_hash_eq=True)

    def cast_vtable_to_hashable(self, cpu, ptr):
        adr = llmemory.cast_ptr_to_adr(ptr)
        return heaptracker.adr2int(adr)

    def getaddr_for_box(self, box):
        return box.getaddr()

def rd_eq(ref1, ref2):
    return ref1 == ref2

def rd_hash(ref):
    assert ref
    return lltype.identityhash(ref)

llhelper = LLTypeHelper()
