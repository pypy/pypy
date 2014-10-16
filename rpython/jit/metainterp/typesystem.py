from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.rtyper import rclass
from rpython.rtyper.annlowlevel import cast_base_ptr_to_instance, llstr
from rpython.rtyper.annlowlevel import cast_instance_to_base_ptr
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
    functionptr = staticmethod(lltype.functionptr)
    nullptr = staticmethod(lltype.nullptr)
    cast_instance_to_base_ref = staticmethod(cast_instance_to_base_ptr)
    BASETYPE = llmemory.GCREF
    BoxRef = history.BoxPtr
    ConstRef = history.ConstPtr
    loops_done_with_this_frame_ref = None # patched by compile.py
    NULLREF = history.ConstPtr.value
    CONST_NULL = history.ConstPtr(NULLREF)
    CVAL_NULLREF = None # patched by optimizeopt.py

    def new_ConstRef(self, x):
        ptrval = lltype.cast_opaque_ptr(llmemory.GCREF, x)
        return history.ConstPtr(ptrval)

    def get_typeptr(self, obj):
        return obj.typeptr

    def get_FuncType(self, ARGS, RESULT):
        FUNCTYPE = lltype.FuncType(ARGS, RESULT)
        FUNCPTRTYPE = lltype.Ptr(FUNCTYPE)
        return FUNCTYPE, FUNCPTRTYPE

    def get_superclass(self, TYPE):
        SUPER = TYPE.TO._first_struct()[1]
        if SUPER is None:
            return None
        return lltype.Ptr(SUPER)

    def cast_to_instance_maybe(self, TYPE, instance):
        return lltype.cast_pointer(TYPE, instance)
    cast_to_instance_maybe._annspecialcase_ = 'specialize:arg(1)'

    def cast_fnptr_to_root(self, fnptr):
        return llmemory.cast_ptr_to_adr(fnptr)

    def cls_of_box(self, box):
        obj = box.getref(lltype.Ptr(rclass.OBJECT))
        cls = llmemory.cast_ptr_to_adr(obj.typeptr)
        return history.ConstInt(heaptracker.adr2int(cls))

    def instanceOf(self, instbox, clsbox):
        adr = clsbox.getaddr()
        bounding_class = llmemory.cast_adr_to_ptr(adr, rclass.CLASSTYPE)
        real_instance = instbox.getref(rclass.OBJECTPTR)
        return rclass.ll_isinstance(real_instance, bounding_class)

    def get_exception_box(self, etype):
        return history.ConstInt(etype)

    def get_exc_value_box(self, evalue):
        return history.BoxPtr(evalue)

    def get_exception_obj(self, evaluebox):
        # only works when translated
        obj = evaluebox.getref(lltype.Ptr(rclass.OBJECT))
        return cast_base_ptr_to_instance(Exception, obj)

    def cast_to_baseclass(self, value):
        return lltype.cast_opaque_ptr(lltype.Ptr(rclass.OBJECT), value)

    @specialize.ll()
    def getlength(self, array):
        return len(array)

    @specialize.ll()
    def getarrayitem(self, array, i):
        return array[i]

    @specialize.ll()
    def setarrayitem(self, array, i, newvalue):
        array[i] = newvalue

    def conststr(self, str):
        ll = llstr(str)
        return history.ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, ll))

    # A dict whose keys are refs (like the .value of BoxPtr).
    # It is an r_dict on lltype.  Two copies, to avoid conflicts with
    # the value type.  Note that NULL is not allowed as a key.
    def new_ref_dict(self):
        return r_dict(rd_eq, rd_hash)
    def new_ref_dict_2(self):
        return r_dict(rd_eq, rd_hash)

    def cast_vtable_to_hashable(self, cpu, ptr):
        adr = llmemory.cast_ptr_to_adr(ptr)
        return heaptracker.adr2int(adr)

    def cast_from_ref(self, TYPE, value):
        return lltype.cast_opaque_ptr(TYPE, value)
    cast_from_ref._annspecialcase_ = 'specialize:arg(1)'

    def cast_to_ref(self, value):
        return lltype.cast_opaque_ptr(llmemory.GCREF, value)
    cast_to_ref._annspecialcase_ = 'specialize:ll'

    def getaddr_for_box(self, box):
        return box.getaddr()

def rd_eq(ref1, ref2):
    return ref1 == ref2

def rd_hash(ref):
    assert ref
    return lltype.identityhash(ref)

llhelper = LLTypeHelper()
