from pypy.rpython.lltypesystem import lltype
from pypy.translator.llvm.node import Node

class TypeDefNode(Node):
    __slots__ = "".split()
    
    def writetypedef(self, codewriter):
        " write out the type definition "

class ArrayTypeNode(TypeDefNode):
    __slots__ = "db ARRAY ARRAYTYPE".split()
    prefix = '%arraytype_'

    def __init__(self, db, ARRAY):
        assert isinstance(ARRAY, lltype.Array)
        self.db = db
        self.ARRAY = ARRAY

        name = ""
        T = ARRAY.OF
        if isinstance(T, lltype.Ptr):
            name += "ptr_"
            T = T.TO
        if hasattr(T, "_name"):            
            name += T._name
        else:
            name += str(T)

        self.make_name(name)
        
    def setup(self):
        self.db.prepare_type(self.ARRAY.OF)

    def writetypedef(self, codewriter):
        if self.ARRAY._hints.get("nolength", False):
            codewriter.typedef(self.ref, 
                               "%s" % self.db.repr_type(self.ARRAY.OF))
        else:
            codewriter.typedef(self.ref, 
                               "{ %s, [0 x %s] }" % (self.db.get_machine_word(),
                                                     self.db.repr_type(self.ARRAY.OF)))

class VoidArrayTypeNode(TypeDefNode):
    " void arrays dont have any real elements "
    __slots__ = "db ARRAY".split()
    prefix = '%voidarraytype_'

    def __init__(self, db, ARRAY):
        assert isinstance(ARRAY, lltype.Array)
        assert not ARRAY._hints.get("nolength", False) 

        self.db = db
        self.ARRAY = ARRAY
        self.make_name()

    def writetypedef(self, codewriter):
        codewriter.typedef(self.ref, "{ %s }" % self.db.get_machine_word())

class StructTypeNode(TypeDefNode):
    __slots__ = "db STRUCT".split()
    prefix = '%structtype_'

    def __init__(self, db, STRUCT): 
        assert isinstance(STRUCT, lltype.Struct)
        self.db = db
        self.STRUCT = STRUCT
        self.make_name(self.STRUCT._name)

    def _fields(self):
        return [getattr(self.STRUCT, name) 
                for name in self.STRUCT._names_without_voids()]
    
    def setup(self):
        for F in self._fields():
            self.db.prepare_type(F)

    def writetypedef(self, codewriter):
        fields_types = [self.db.repr_type(F) for F in self._fields()]
        codewriter.typedef(self.ref, 
                           "{ %s }" % ", ".join(fields_types))

class FixedSizeArrayTypeNode(StructTypeNode):
    prefix = '%fixarray_'

    def setup(self):
        FIELDS = self._fields()
        if FIELDS:
            self.db.prepare_type(FIELDS[0])
            
    def writetypedef(self, codewriter):
        codewriter.typedef(self.ref,
                           "[%s x %s]" % (self.STRUCT.length, 
                                          self.db.repr_type(self.STRUCT.OF)))

class FuncTypeNode(TypeDefNode):
    __slots__ = "db T".split()
    prefix = '%functiontype'

    def __init__(self, db, T):
        assert isinstance(T, lltype.FuncType)

        self.db = db
        self.T = T
        self.make_name()

    def setup(self):
        self.db.prepare_type(self.T.RESULT)
        self.db.prepare_type_multi(self.T._trueargs())

    def writetypedef(self, codewriter):
        returntype = self.db.repr_type(self.T.RESULT)
        inputargtypes = [self.db.repr_type(a) for a in self.T._trueargs()]
        codewriter.typedef(self.ref, 
                           "%s (%s)" % (returntype, 
                                        ", ".join(inputargtypes)))

class OpaqueTypeNode(TypeDefNode):
    def __init__(self, db, T): 
        assert isinstance(T, lltype.OpaqueType)
        self.db = db
        self.T = T
        self.make_name("RPyOpaque_%s" % (T.tag))
        
    def writetypedef(self, codewriter):
        codewriter.typedef(self.ref, "opaque*")

class ExtOpaqueTypeNode(OpaqueTypeNode):
    def writetypedef(self, codewriter):
        pass

def create_typedef_node(db, TYPE):
    if isinstance(TYPE, lltype.FixedSizeArray):
        return FixedSizeArrayTypeNode(db, TYPE)

    elif isinstance(TYPE, lltype.Struct):
        return StructTypeNode(db, TYPE)
        
    elif isinstance(TYPE, lltype.FuncType):
        return FuncTypeNode(db, TYPE)
        
    elif isinstance(TYPE, lltype.Array):
        if TYPE.OF is lltype.Void:
            return VoidArrayTypeNode(db, TYPE)
        else:
            return ArrayTypeNode(db, TYPE)

    elif isinstance(TYPE, lltype.OpaqueType):
        if hasattr(TYPE, '_exttypeinfo'):
            return ExtOpaqueTypeNode(db, TYPE)
        else:
            return OpaqueTypeNode(db, TYPE)
            
    else:
        assert False, "create_typedef_node %s %s" % (TYPE, type(TYPE))
        
