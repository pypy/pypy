import py
from pypy.rpython import lltype
from pypy.translator.js.node import LLVMNode, ConstantLLVMNode
from pypy.translator.js.log import log
log = log.structnode

class ArrayTypeNode(LLVMNode):
    __slots__ = "db array arraytype ref constructor_ref constructor_decl".split()

    def __init__(self, db, array):
        assert isinstance(array, lltype.Array)
        self.db = db
        self.array = array
        self.arraytype = arraytype = array.OF
        # ref is used to reference the arraytype in llvm source 
        # constructor_ref is used to reference the constructor 
        # for the array type in llvm source code 
        # constructor_decl is used to declare the constructor
        # for the array type (see writeimpl)
        name = ""        
        if isinstance(arraytype, lltype.Ptr):
            name += "ptr_"
            arraytype = arraytype.TO
        if hasattr(arraytype, "_name"):            
            name += arraytype._name
        else:
            name += str(arraytype)

        self.ref = self.make_ref('arraytype_', name)
        self.constructor_ref = 'new Array'
        self.constructor_decl = "%s(len)" % self.constructor_ref

    def __str__(self):
        return "<ArrayTypeNode %r>" % self.ref
        
    def setup(self):
        self.db.prepare_type(self.arraytype)

    # ______________________________________________________________________
    # entry points from genllvm
    #
    #def writedatatypedecl(self, codewriter):
    #    codewriter.arraydef(self.ref,
    #                        'int',
    #                        self.db.repr_type(self.arraytype))

    #def writedecl(self, codewriter): 
    #    # declaration for constructor
    #    codewriter.declare(self.constructor_decl)


class VoidArrayTypeNode(LLVMNode):
    __slots__ = "db array ref".split()

    def __init__(self, db, array):
        assert isinstance(array, lltype.Array)
        self.db = db
        self.array = array
        self.ref = "arraytype_Void"

    #def writedatatypedecl(self, codewriter):
    #    td = "%s = type { int }" % self.ref
    #    codewriter.append(td)
        
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
        prefix = 'arrayinstance'
        name = '' #str(value).split()[1]
        self.ref = self.make_ref(prefix, name)

    def __str__(self):
        return "<ArrayNode %r>" % (self.ref,)

    def setup(self):
        for item in self.value.items:
            self.db.prepare_constant(self.arraytype, item)

        p, c = lltype.parentlink(self.value)
        p, c = lltype.parentlink(self.value)
        if p is not None:
            self.db.prepare_constant(lltype.typeOf(p), p)

    def writedecl(self, codewriter):
        if self.arraytype is lltype.Char:  #or use seperate nodetype
            codewriter.declare(self.ref + ' = new String()')
        else:
            codewriter.declare(self.ref + ' = new Array()')

    def get_length(self):
        """ returns logical length of array """
        items = self.value.items
        return len(items)

    def get_arrayvalue(self):
        items = self.value.items
        l = len(items)
        #r = "[%s]" % ", ".join([self.db.repr_constant(v)[1] for v in items])
        r = "[%s]" % ", ".join([str(v) for v in items])
        return l, r 

    def get_typerepr(self):
        arraylen = self.get_arrayvalue()[0]
        typeval = self.db.repr_type(self.arraytype)
        return "{ int, [%s x %s] }" % (arraylen, typeval)

    def get_ref(self):
        return self.ref
        #typeval = self.db.repr_type(lltype.typeOf(self.value))
        #ref = "cast (%s* %s to %s*)" % (self.get_typerepr(), self.ref, typeval)
        #p, c = lltype.parentlink(self.value)
        #assert p is None, "child arrays are NOT needed by rtyper"
        #return ref

    def get_pbcref(self, toptr):
        return self.ref
        #ref = self.ref
        #p, c = lltype.parentlink(self.value)
        #assert p is None, "child arrays are NOT needed by rtyper"
        #
        #fromptr = "%s*" % self.get_typerepr()
        #ref = "cast(%s %s to %s)" % (fromptr, ref, toptr)
        #return ref

    def get_childref(self, index):
        return "getelementptr(%s* %s, int 0, uint 1, int %s)" %(
            self.get_typerepr(),
            self.ref,
            index)
    
    def constantvalue(self):
        physicallen, arrayrepr = self.get_arrayvalue()
        return arrayrepr

        ## first length is logical, second is physical
        #typeval = self.db.repr_type(self.arraytype)
        #value = "int %s, [%s x %s] %s" % (self.get_length(),
        #                                  physicallen,
        #                                  typeval,
        #                                  arrayrepr)
        #
        #s = "%s {%s}" % (self.get_typerepr(), value)
        #return s
    
class StrArrayNode(ArrayNode):
    __slots__ = "".split()

    printables = dict([(ord(i), None) for i in
      ("0123456789abcdefghijklmnopqrstuvwxyz" +
       "ABCDEFGHIJKLMNOPQRSTUVWXYZ" +
       "!#$%&()*+,-./:;<=>?@[]^_`{|}~ '")])

    def get_arrayvalue(self):
        items = self.value.items
        item_length = len(items)
        s = []
        for c in items:
            if ord(c) in StrArrayNode.printables:
                s.append(c)
            else:
                s.append("\\%02x" % ord(c))
                
        r = '"%s"' % "".join(s)
        return item_length, r

class VoidArrayNode(ConstantLLVMNode):
    __slots__ = "db value ref".split()

    def __init__(self, db, value):
        assert isinstance(lltype.typeOf(value), lltype.Array)
        self.db = db
        self.value = value
        prefix = 'arrayinstance'
        name = '' #str(value).split()[1]
        self.ref = self.make_ref(prefix, name)

    def constantvalue(self):
        return "{ int } {int %s}" % len(self.value.items)
