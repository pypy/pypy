from pypy.lang.smalltalk.model import \
     W_Class, W_MetaClass, W_SmallInteger, POINTERS, BYTES

# ___________________________________________________________________________
# Core Bootstrapping Objects

classtable = {}
def create_classtable():
    def define_core_cls(clsnm, clsobj):
        clsobj.name = clsnm
        classtable[clsnm] = clsobj
        globals()[clsnm] = clsobj
        return clsobj
    
    #    Class Name            Super class name
    cls_nm_tbl = [
        ["w_Object",           "w_ProtoObject"],
        ["w_Behavior",         "w_Object"],
        ["w_ClassDescription", "w_Behavior"],
        ["w_Class",            "w_ClassDescription"],
        ["w_Metaclass",        "w_ClassDescription"],
        ]
    define_core_cls("w_ProtoObjectClass", W_MetaClass(None, None))
    define_core_cls("w_ProtoObject", W_Class(w_ProtoObjectClass, None))
    for (cls_nm, super_cls_nm) in cls_nm_tbl:
        meta_nm = cls_nm + "Class"
        meta_super_nm = super_cls_nm + "Class"
        metacls = define_core_cls(
            meta_nm, W_MetaClass(None, classtable[meta_super_nm], name=meta_nm))
        define_core_cls(
            cls_nm, W_Class(metacls, classtable[super_cls_nm], name=cls_nm))
    w_ProtoObjectClass.w_superclass = w_Class
    for nm, w_cls_obj in classtable.items():
        if w_cls_obj.ismetaclass():
            w_cls_obj.w_class = w_Metaclass
create_classtable()

# ___________________________________________________________________________
# Other classes

def define_cls(cls_nm, supercls_nm, instvarsize=0, format=POINTERS):
    meta_nm = cls_nm + "Class"
    meta_super_nm = supercls_nm + "Class"
    w_meta_cls = globals()[meta_nm] = classtable[meta_nm] = \
                 W_MetaClass(w_Metaclass,
                             classtable[meta_super_nm],
                             name=meta_nm)
    w_cls = globals()[cls_nm] = classtable[cls_nm] = \
            W_Class(w_meta_cls,
                    classtable[supercls_nm],
                    name=cls_nm,
                    instvarsize=instvarsize,
                    format=format)

define_cls("w_Magnitude", "w_Object")
define_cls("w_Character", "w_Magnitude", instvarsize=1)
define_cls("w_Number", "w_Magnitude")
define_cls("w_Integer", "w_Number")
define_cls("w_SmallInteger", "w_Integer")
define_cls("w_Float", "w_Number")
define_cls("w_Collection", "w_Object")
define_cls("w_SequencableCollection", "w_Collection")
define_cls("w_ArrayedCollection", "w_SequencableCollection")
define_cls("w_String", "w_ArrayedCollection")
define_cls("w_ByteString", "w_String", format=BYTES)
define_cls("w_UndefinedObject", "w_Object")
define_cls("w_Boolean", "w_Object")
define_cls("w_True", "w_Boolean")
define_cls("w_False", "w_Boolean")
