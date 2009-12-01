from pypy.rpython.lltypesystem import lltype, llmemory, rclass
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.annlowlevel import cast_base_ptr_to_instance, llstr, oostr
from pypy.rpython.annlowlevel import cast_instance_to_base_ptr
from pypy.rpython.annlowlevel import cast_instance_to_base_obj
from pypy.jit.metainterp import history
from pypy.rlib.objectmodel import r_dict

def deref(T):
    if isinstance(T, lltype.Ptr):
        return T.TO
    assert isinstance(T, ootype.OOType)
    return T

def fieldType(T, name):
    if isinstance(T, lltype.Struct):
        return getattr(T, name)
    elif isinstance(T, (ootype.Instance, ootype.Record)):
##         if name == '__class__':
##             # XXX hack hack hack
##             return ootype.Class
        _, FIELD = T._lookup_field(name)
        return FIELD
    else:
        assert False

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
    ConstAddr = history.ConstAddr
    loops_done_with_this_frame_ref = None # patched by compile.py
    CONST_NULL = history.ConstPtr(history.ConstPtr.value)
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
        return lltype.Ptr(TYPE.TO._first_struct()[1])

    def cast_to_instance_maybe(self, TYPE, instance):
        return lltype.cast_pointer(TYPE, instance)
    cast_to_instance_maybe._annspecialcase_ = 'specialize:arg(1)'

    def cast_fnptr_to_root(self, fnptr):
        return llmemory.cast_ptr_to_adr(fnptr)

    def cls_of_box(self, cpu, box):
        obj = box.getref(lltype.Ptr(rclass.OBJECT))
        cls = llmemory.cast_ptr_to_adr(obj.typeptr)
        return history.ConstInt(cpu.cast_adr_to_int(cls))

    def subclassOf(self, cpu, clsbox1, clsbox2):
        adr = clsbox2.getaddr(cpu)
        bounding_class = llmemory.cast_adr_to_ptr(adr, rclass.CLASSTYPE)
        adr = clsbox1.getaddr(cpu)
        real_class = llmemory.cast_adr_to_ptr(adr, rclass.CLASSTYPE)
        return rclass.ll_issubclass(real_class, bounding_class)

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

    def getlength(self, array):
        return len(array)

    def getarrayitem(self, array, i):
        return array[i]

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
        return cpu.cast_adr_to_int(adr)

    def cast_from_ref(self, TYPE, value):
        return lltype.cast_opaque_ptr(TYPE, value)
    cast_from_ref._annspecialcase_ = 'specialize:arg(1)'

    def cast_to_ref(self, value):
        return lltype.cast_opaque_ptr(llmemory.GCREF, value)
    cast_to_ref._annspecialcase_ = 'specialize:ll'
    
    def getaddr_for_box(self, cpu, box):
        return box.getaddr(cpu)

def rd_eq(ref1, ref2):
    return ref1 == ref2

def rd_hash(ref):
    assert ref
    return lltype.identityhash(ref)

# ____________________________________________________________

class OOTypeHelper(TypeSystemHelper):

    name = 'ootype'
    functionptr = staticmethod(ootype.static_meth)
    nullptr = staticmethod(ootype.null)
    cast_instance_to_base_ref = staticmethod(cast_instance_to_base_obj)
    BASETYPE = ootype.Object
    BoxRef = history.BoxObj
    ConstRef = history.ConstObj
    ConstAddr = history.ConstObj
    loops_done_with_this_frame_ref = None # patched by compile.py
    CONST_NULL = history.ConstObj(history.ConstObj.value)
    CVAL_NULLREF = None # patched by optimizeopt.py
    
    def new_ConstRef(self, x):
        obj = ootype.cast_to_object(x)
        return history.ConstObj(obj)

    def get_typeptr(self, obj):
        return ootype.classof(obj)

    def get_FuncType(self, ARGS, RESULT):
        FUNCTYPE = ootype.StaticMethod(ARGS, RESULT)
        return FUNCTYPE, FUNCTYPE

    def get_superclass(self, TYPE):
        return TYPE._superclass

    def cast_to_instance_maybe(self, TYPE, instance):
        return instance
    cast_to_instance_maybe._annspecialcase_ = 'specialize:arg(1)'

    def cast_fnptr_to_root(self, fnptr):
        return ootype.cast_to_object(fnptr)

    def cls_of_box(self, cpu, box):
        obj = box.getref(ootype.ROOT)
        oocls = ootype.classof(obj)
        return history.ConstObj(ootype.cast_to_object(oocls))

    def subclassOf(self, cpu, clsbox1, clsbox2):
        cls1 = clsbox1.getref(ootype.Class)
        cls2 = clsbox2.getref(ootype.Class)
        return ootype.subclassof(cls1, cls2)

    def get_exception_box(self, etype):
        return history.ConstObj(etype)

    def get_exc_value_box(self, evalue):
        return history.BoxObj(evalue)

    def get_exception_obj(self, evaluebox):
        # only works when translated
        obj = evaluebox.getref(ootype.ROOT)
        return cast_base_ptr_to_instance(Exception, obj)

    def cast_to_baseclass(self, value):
        return ootype.cast_from_object(ootype.ROOT, value)

    def getlength(self, array):
        return array.ll_length()

    def getarrayitem(self, array, i):
        return array.ll_getitem_fast(i)

    def setarrayitem(self, array, i, newvalue):
        array.ll_setitem_fast(i, newvalue)

    def conststr(self, str):
        oo = oostr(str)
        return history.ConstObj(ootype.cast_to_object(oo))

    # A dict whose keys are refs (like the .value of BoxObj).
    # It is a normal dict on ootype.  Two copies, to avoid conflicts
    # with the value type.
    def new_ref_dict(self):
        return {}
    def new_ref_dict_2(self):
        return {}

    def cast_vtable_to_hashable(self, cpu, obj):
        return ootype.cast_to_object(obj)

    def cast_from_ref(self, TYPE, value):
        return ootype.cast_from_object(TYPE, value)
    cast_from_ref._annspecialcase_ = 'specialize:arg(1)'

    def cast_to_ref(self, value):
        return ootype.cast_to_object(value)
    cast_to_ref._annspecialcase_ = 'specialize:ll'

    def getaddr_for_box(self, cpu, box):
        return box.getref_base()
    
llhelper = LLTypeHelper()
oohelper = OOTypeHelper()
