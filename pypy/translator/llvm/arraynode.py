from pypy.rpython.lltypesystem import lltype
from pypy.translator.llvm.log import log
from pypy.translator.llvm.node import LLVMNode, ConstantLLVMNode
log = log.structnode

class ArrayTypeNode(LLVMNode):
    __slots__ = "db array arraytype ref".split()

    def __init__(self, db, array):
        assert isinstance(array, lltype.Array)
        self.db = db
        self.array = array
        self.arraytype = arraytype = array.OF
        name = ""        
        if isinstance(arraytype, lltype.Ptr):
            name += "ptr_"
            arraytype = arraytype.TO
        if hasattr(arraytype, "_name"):            
            name += arraytype._name
        else:
            name += str(arraytype)

        self.ref = self.make_ref('%arraytype_', name)

    def __str__(self):
        return "<ArrayTypeNode %r>" % self.ref
        
    def setup(self):
        self.db.prepare_type(self.arraytype)

    # ______________________________________________________________________
    # entry points from genllvm
    #
    def writedatatypedecl(self, codewriter):
        if self.array._hints.get("nolength", False):
            codewriter.arraynolendef(self.ref,
                                     self.db.repr_type(self.arraytype))
        else:
            codewriter.arraydef(self.ref,
                                self.db.get_machine_word(),
                                self.db.repr_type(self.arraytype))

class VoidArrayTypeNode(LLVMNode):
    __slots__ = "db array ref".split()

    def __init__(self, db, array):
        assert isinstance(array, lltype.Array)
        self.db = db
        self.array = array
        self.ref = "%arraytype_Void"

    def writedatatypedecl(self, codewriter):
        assert not self.array._hints.get("nolength", False) 
        codewriter.typedef(self.ref, "{ %s }" % self.db.get_machine_word())
        
class ArrayNode(ConstantLLVMNode):
    """ An arraynode.  Elements can be
    a primitive,
    a struct,
    pointer to struct/array
    """
    __slots__ = "db value arraytype ref".split()
    
    def __init__(self, db, value):
        assert isinstance(lltype.typeOf(value), lltype.Array)
        self.db = db
        self.value = value
        self.arraytype = lltype.typeOf(value).OF
        prefix = '%arrayinstance'
        name = '' #str(value).split()[1]
        self.ref = self.make_ref(prefix, name)

    def __str__(self):
        return "<ArrayNode %r>" % (self.ref,)

    def setup(self):
        for item in self.value.items:
            self.db.prepare_constant(self.arraytype, item)

        p, c = lltype.parentlink(self.value)
        if p is not None:
            self.db.prepare_constant(lltype.typeOf(p), p)

    def get_length(self):
        """ returns logical length of array """
        items = self.value.items
        return len(items)

    def get_arrayvalue(self):
        items = self.value.items
        l = len(items)
        r = "[%s]" % ", ".join([self.db.repr_constant(v)[1] for v in items])
        return l, r 

    def get_typerepr(self):
        arraylen = self.get_arrayvalue()[0]
        typeval = self.db.repr_type(self.arraytype)
        return "{ %s, [%s x %s] }" % (self.db.get_machine_word(),
                                      arraylen, typeval)

    def get_ref(self):
        typeval = self.db.repr_type(lltype.typeOf(self.value))
        p, c = lltype.parentlink(self.value)
        if p is None:
            ref = self.ref
        else:
            ref = self.db.get_childref(p, c)

        ref = "cast(%s* %s to %s*)" % (self.get_typerepr(),
                                       ref,
                                       typeval)
        return ref

    def get_pbcref(self, toptr):
        ref = self.ref
        p, c = lltype.parentlink(self.value)
        assert p is None, "child PBC arrays are NOT needed by rtyper"

        fromptr = "%s*" % self.get_typerepr()
        ref = "cast(%s %s to %s)" % (fromptr, ref, toptr)
        return ref

    def get_childref(self, index):
        return "getelementptr(%s* %s, int 0, uint 1, int %s)" %(
            self.get_typerepr(),
            self.ref,
            index)
    
    def constantvalue(self):
        physicallen, arrayrepr = self.get_arrayvalue()
        typeval = self.db.repr_type(self.arraytype)

        # first length is logical, second is physical
        value = "%s %s, [%s x %s] %s" % (self.db.get_machine_word(),
                                         self.get_length(),
                                         physicallen,
                                         typeval,
                                         arrayrepr)

        s = "%s {%s}" % (self.get_typerepr(), value)
        return s

class ArrayNoLengthNode(ArrayNode):
    def get_typerepr(self):
        arraylen = self.get_arrayvalue()[0]
        typeval = self.db.repr_type(self.arraytype)
        return "{ [%s x %s] }" % (arraylen, typeval)
    
    def get_childref(self, index):
        return "getelementptr(%s* %s, int 0, int %s)" %(
            self.get_typerepr(),
            self.ref,
            index)

    def constantvalue(self):
        physicallen, arrayrepr = self.get_arrayvalue()
        typeval = self.db.repr_type(self.arraytype)

        value = "[%s x %s] %s" % (physicallen,
                                  typeval,
                                  arrayrepr)

        s = "%s {%s}" % (self.get_typerepr(), value)
        return s

class StrArrayNode(ArrayNode):
    __slots__ = "".split()

    printables = dict([(ord(i), None) for i in
      ("0123456789abcdefghijklmnopqrstuvwxyz" +
       "ABCDEFGHIJKLMNOPQRSTUVWXYZ" +
       "!#$%&()*+,-./:;<=>?@[]^_`{|}~ '")])

    def get_arrayvalue(self):
        items = self.value.items
        item_length = len(items)
        if item_length == 0 or items[-1] != chr(0):
            items = items + [chr(0)]
            item_length += 1
        s = []
        for c in items:
            if ord(c) in StrArrayNode.printables:
                s.append(c)
            else:
                s.append("\\%02x" % ord(c))
                
        r = 'c"%s"' % "".join(s)
        return item_length, r

class VoidArrayNode(ConstantLLVMNode):
    __slots__ = "db value ref".split()

    def __init__(self, db, value):
        assert isinstance(lltype.typeOf(value), lltype.Array)
        self.db = db
        self.value = value
        prefix = '%arrayinstance'
        name = '' #str(value).split()[1]
        self.ref = self.make_ref(prefix, name)

    def constantvalue(self):
        return "{ %s } {%s %s}" % (self.db.get_machine_word(),
                                   self.db.get_machine_word(),
                                   len(self.value.items))
