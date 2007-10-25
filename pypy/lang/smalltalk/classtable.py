from pypy.lang.smalltalk import mirror

def bootstrap_classmirror(instsize, m_superclass=None, m_metaclass=None,
                          name='?', format=mirror.POINTERS, varsized=False):
    from pypy.lang.smalltalk import model
    w_class = model.W_Object()     # a dummy placeholder for testing
    m = mirror.ClassMirror(w_class)
    m.methoddict = {}
    m.m_superclass = m_superclass
    m.m_metaclass = m_metaclass
    m.name = name
    m.instance_size = instsize
    m.instance_kind = format
    m.instance_varsized = varsized or format != mirror.POINTERS
    m.invalid = False
    mirror.mirrorcache.cache[w_class] = m
    return m

# ___________________________________________________________________________
# Core Bootstrapping Objects

classtable = {}
def create_classtable():
    def define_core_cls(name, m_superclass, m_metaclass):
        assert name.startswith('m_')
        mirror = bootstrap_classmirror(instsize=0,    # XXX
                                       m_superclass=m_superclass,
                                       m_metaclass=m_metaclass,
                                       name=name[2:])
        classtable[name] = mirror
        globals()[name] = mirror
        return mirror
    
    #    Class Name            Super class name
    cls_nm_tbl = [
        ["m_Object",           "m_ProtoObject"],
        ["m_Behavior",         "m_Object"],
        ["m_ClassDescription", "m_Behavior"],
        ["m_Class",            "m_ClassDescription"],
        ["m_Metaclass",        "m_ClassDescription"],
        ]
    define_core_cls("m_ProtoObjectClass", None, None)
    define_core_cls("m_ProtoObject", None, m_ProtoObjectClass)
    for (cls_nm, super_cls_nm) in cls_nm_tbl:
        meta_nm = cls_nm + "Class"
        meta_super_nm = super_cls_nm + "Class"
        m_metacls = define_core_cls(meta_nm, classtable[meta_super_nm], None)
        define_core_cls(cls_nm, classtable[super_cls_nm], m_metacls)
    m_ProtoObjectClass.m_superclass = m_Class
    # at this point, all classes that still lack a m_metaclass are themselves
    # metaclasses
    for nm, m_cls_obj in classtable.items():
        if m_cls_obj.m_metaclass is None:
            m_cls_obj.m_metaclass = m_Metaclass
create_classtable()

# ___________________________________________________________________________
# Other classes

def define_cls(cls_nm, supercls_nm, instvarsize=0, format=mirror.POINTERS):
    assert cls_nm.startswith("m_")
    meta_nm = cls_nm + "Class"
    meta_super_nm = supercls_nm + "Class"
    m_meta_cls = globals()[meta_nm] = classtable[meta_nm] = \
                 bootstrap_classmirror(0,   # XXX
                                       classtable[meta_super_nm],
                                       m_Metaclass,
                                       name=meta_nm[2:])
    m_cls = globals()[cls_nm] = classtable[cls_nm] = \
                 bootstrap_classmirror(instvarsize,
                                       classtable[supercls_nm],
                                       m_meta_cls,
                                       format=format,
                                       name=cls_nm[2:])

define_cls("m_Magnitude", "m_Object")
define_cls("m_Character", "m_Magnitude", instvarsize=1)
define_cls("m_Number", "m_Magnitude")
define_cls("m_Integer", "m_Number")
define_cls("m_SmallInteger", "m_Integer")
define_cls("m_Float", "m_Number", format=mirror.BYTES)
define_cls("m_Collection", "m_Object")
define_cls("m_SequencableCollection", "m_Collection")
define_cls("m_ArrayedCollection", "m_SequencableCollection")
define_cls("m_String", "m_ArrayedCollection")
define_cls("m_ByteString", "m_String", format=mirror.BYTES)
define_cls("m_UndefinedObject", "m_Object")
define_cls("m_Boolean", "m_Object")
define_cls("m_True", "m_Boolean")
define_cls("m_False", "m_Boolean")
define_cls("m_ByteArray", "m_ArrayedCollection", format=mirror.BYTES)
define_cls("m_CompiledMethod", "m_ByteArray", format=mirror.COMPILED_METHOD)
