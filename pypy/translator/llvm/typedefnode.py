from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.translator.llvm.node import Node

def getindexhelper(db, name, struct):
    assert name in list(struct._names)

    fieldnames = struct._names_without_voids()
    try:
        index = fieldnames.index(name)
    except ValueError:
        index = -1
    else:
        index += len(db.gcpolicy.gcheader_definition(struct))
    return index

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
        for name, F in self.db.gcpolicy.gcheader_definition(self.ARRAY):
            self.db.prepare_type(F)

    def get_typerepr(self, arraylen=0):
        gchdr = self.db.gcpolicy.gcheader_definition(self.ARRAY)
        if self.ARRAY._hints.get("nolength", False):
            assert len(gchdr) == 0
            return "%s" % self.db.repr_type(self.ARRAY.OF)
        else:
            fields = [self.db.repr_type(F) for name, F in gchdr]
            fields.append(self.db.get_machine_word())
            fields.append("[%d x %s]" % (arraylen,
                                         self.db.repr_type(self.ARRAY.OF),))
            return "{ %s }" % ", ".join(fields)

    def writetypedef(self, codewriter):
        codewriter.typedef(self.ref, self.get_typerepr())

    def indexref_to_getelementptr(self, indices, indexref):
        TYPE = self.ARRAY
        if not TYPE._hints.get("nolength", False):
            indices.append(("i32", self.indexref_for_items()))
        indices.append(("i32", indexref))
        return TYPE.OF

    def indexref_for_length(self):
        gchdr = self.db.gcpolicy.gcheader_definition(self.ARRAY)
        return len(gchdr) + 0

    def indexref_for_items(self):
        gchdr = self.db.gcpolicy.gcheader_definition(self.ARRAY)
        return len(gchdr) + 1

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

    def setup(self):
        for name, F in self.db.gcpolicy.gcheader_definition(self.ARRAY):
            self.db.prepare_type(F)

    def get_typerepr(self, arraylen=0):
        assert not self.ARRAY._hints.get("nolength", False), "XXX"
        gchdr = self.db.gcpolicy.gcheader_definition(self.ARRAY)
        fields = [self.db.repr_type(F) for name, F in gchdr]
        fields.append(self.db.get_machine_word())
        return "{ %s }" % ", ".join(fields)

    def writetypedef(self, codewriter):
        codewriter.typedef(self.ref, self.get_typerepr())

    def indexref_for_length(self):
        gchdr = self.db.gcpolicy.gcheader_definition(self.ARRAY)
        return len(gchdr) + 0

class StructTypeNode(TypeDefNode):
    __slots__ = "db STRUCT".split()
    prefix = '%structtype_'

    def __init__(self, db, STRUCT): 
        assert isinstance(STRUCT, lltype.Struct)
        self.db = db
        self.STRUCT = STRUCT
        parts = self.STRUCT._name.split('.')
        name = parts[-1]
        self.make_name(name)

    def _fields(self):
        types = []
        for name, T in self.db.gcpolicy.gcheader_definition(self.STRUCT):
            types.append(T)
        for name in self.STRUCT._names_without_voids():
            types.append(getattr(self.STRUCT, name))
        return types

    def setup(self):
        for F in self._fields():
            self.db.prepare_type(F)

    def writetypedef(self, codewriter):
        fields_types = [self.db.repr_type(F) for F in self._fields()]
        codewriter.typedef(self.ref, 
                           "{ %s }" % ", ".join(fields_types))

    def fieldname_to_getelementptr(self, indices, name):
        TYPE = self.STRUCT
        indexref = getindexhelper(self.db, name, TYPE)
        indices.append(("i32", indexref))
        return getattr(TYPE, name)

class FixedSizeArrayTypeNode(StructTypeNode):
    prefix = '%fixarray_'

    def setup(self):
        assert self.STRUCT._gckind != 'gc'
        FIELDS = self._fields()
        if FIELDS:
            self.db.prepare_type(FIELDS[0])
            
    def writetypedef(self, codewriter):
        codewriter.typedef(self.ref,
                           "[%s x %s]" % (self.STRUCT.length, 
                                          self.db.repr_type(self.STRUCT.OF)))

    def indexref_to_getelementptr(self, indices, indexref):
        TYPE = self.STRUCT
        assert TYPE._gckind != 'gc'
        indices.append(("i32", indexref))
        return TYPE.OF

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
        if TYPE.hints.get("render_structure", False):
            return ExtOpaqueTypeNode(db, TYPE)
        else:
            return OpaqueTypeNode(db, TYPE)

    elif TYPE == llmemory.WeakRef:
        REALT = db.gcpolicy.get_real_weakref_type()
        return create_typedef_node(db, REALT)

    else:
        assert False, "create_typedef_node %s %s" % (TYPE, type(TYPE))
        
