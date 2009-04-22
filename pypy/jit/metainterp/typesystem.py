#from pypy.rpython.annlowlevel import base_ptr_lltype, base_obj_ootype
#from pypy.rpython.annlowlevel import cast_instance_to_base_ptr
#from pypy.rpython.annlowlevel import cast_instance_to_base_obj
from pypy.rpython.lltypesystem import lltype, llmemory, rclass
from pypy.rpython.ootypesystem import ootype
from pypy.jit.metainterp import history

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

class TypeSystemHelper(object):

    def _freeze_(self):
        return True

class LLTypeHelper(TypeSystemHelper):

    name = 'lltype'
    functionptr = staticmethod(lltype.functionptr)
    #ROOT_TYPE = llmemory.Address
    #BASE_OBJ_TYPE = base_ptr_lltype()
    #NULL_OBJECT = base_ptr_lltype()._defl()
    #cast_instance_to_base_ptr = staticmethod(cast_instance_to_base_ptr)

    def get_typeptr(self, obj):
        return obj.typeptr

    def get_FuncType(self, ARGS, RESULT):
        FUNCTYPE = lltype.FuncType(ARGS, RESULT)
        FUNCPTRTYPE = lltype.Ptr(FUNCTYPE)
        return FUNCTYPE, FUNCPTRTYPE

    def cast_fnptr_to_root(self, fnptr):
        return llmemory.cast_ptr_to_adr(fnptr)

    def cls_of_box(self, cpu, box):
        obj = box.getptr(lltype.Ptr(rclass.OBJECT))
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

    @staticmethod
    def unwrap_exc_value_box(valuebox):
        return valuebox.getptr(lltype.Ptr(rclass.OBJECT))

class OOTypeHelper(TypeSystemHelper):

    name = 'ootype'
    functionptr = staticmethod(ootype.static_meth)
    #ROOT_TYPE = ootype.Object
    #BASE_OBJ_TYPE = base_obj_ootype()
    #NULL_OBJECT = base_obj_ootype()._defl()
    #cast_instance_to_base_ptr = staticmethod(cast_instance_to_base_obj)

    def get_typeptr(self, obj):
        return obj.meta

    def get_FuncType(self, ARGS, RESULT):
        FUNCTYPE = ootype.StaticMethod(ARGS, RESULT)
        return FUNCTYPE, FUNCTYPE

    def cast_fnptr_to_root(self, fnptr):
        return ootype.cast_to_object(fnptr)

    def cls_of_box(self, cpu, box):
        obj = ootype.cast_from_object(ootype.ROOT, box.getobj())
        oocls = ootype.classof(obj)
        return history.ConstObj(ootype.cast_to_object(oocls))

    def subclassOf(self, cpu, clsbox1, clsbox2):
        cls1 = ootype.cast_from_object(ootype.Class, clsbox1.getobj())
        cls2 = ootype.cast_from_object(ootype.Class, clsbox2.getobj())
        return ootype.subclassof(cls1, cls2)

    def get_exception_box(self, etype):
        return history.ConstObj(etype)

    def get_exc_value_box(self, evalue):
        return history.BoxObj(evalue)

    @staticmethod
    def unwrap_exc_value_box(valuebox):
        return ootype.cast_from_object(ootype.ROOT, valuebox.getobj())


llhelper = LLTypeHelper()
oohelper = OOTypeHelper()
