import py
from pypy.rpython import lltype
from pypy.translator.llvm2.log import log
from pypy.translator.llvm2.node import LLVMNode, ConstantLLVMNode
from pypy.translator.llvm2 import varsize 
log = log.structnode

class ArrayTypeNode(LLVMNode):
    def __init__(self, db, array):
        assert isinstance(array, lltype.Array)

        self.db = db
        self.array = array
        arraytype = self.arraytype = array.OF
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

        self.ref = self.make_ref('%arraytype.', name)
        self.constructor_ref = self.make_ref('%new.array.', name)
        self.constructor_decl = "%s * %s(%s %%len)" % \
                                (self.ref,
                                 self.constructor_ref,
                                 self.db.get_machine_word())

    def __str__(self):
        return "<ArrayTypeNode %r>" % self.ref
        
    def setup(self):
        self.db.prepare_type(self.arraytype)

    def is_atomic(self):
        if isinstance(self.arraytype, lltype.Primitive):
            return True
        elif isinstance(self.arraytype, lltype.Ptr):
            return False
        else:
            return self.db.is_atomic(self.arraytype)
            
    # ______________________________________________________________________
    # entry points from genllvm
    #
    def writedatatypedecl(self, codewriter):
        codewriter.arraydef(self.ref,
                            self.db.get_machine_word(),
                            self.db.repr_type(self.arraytype))

    def writedecl(self, codewriter): 
        # declaration for constructor
        codewriter.declare(self.constructor_decl)

    def writeimpl(self, codewriter):
        log.writeimpl(self.ref)
        fromtype = self.db.repr_type(self.arraytype) 
        varsize.write_constructor(self.db, codewriter, self.ref, 
                                  self.constructor_decl,
                                  fromtype,
                                  atomicmalloc=self.is_atomic())

class VoidArrayTypeNode(LLVMNode):

    def __init__(self, db, array):
        assert isinstance(array, lltype.Array)
        self.db = db
        self.ref = "%arraytype.Void"

    def writedatatypedecl(self, codewriter):
        td = "%s = type { %s }" % (self.ref, self.db.get_machine_word())
        codewriter.append(td)
        
    def is_atomic(self):
        return True

class ArrayNode(ConstantLLVMNode):
    """ An arraynode.  Elements can be
    a primitive,
    a struct,
    pointer to struct/array
    """
    def __init__(self, db, value):
        assert isinstance(lltype.typeOf(value), lltype.Array)
        self.db = db
        self.value = value
        self.arraytype = lltype.typeOf(value).OF
        self.ref = self.make_ref('%arrayinstance', '')

    def __str__(self):
        return "<ArrayNode %r>" % (self.ref,)

    def setup(self):
        for item in self.value.items:
            self.db.prepare_constant(self.arraytype, item)

        p, c = lltype.parentlink(self.value)
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
        ref = "cast (%s* %s to %s*)" % (self.get_typerepr(),
                                        self.ref,
                                        typeval)

        p, c = lltype.parentlink(self.value)
        assert p is None, "child arrays are NOT needed by rtyper"
        return ref

    def get_pbcref(self, toptr):
        ref = self.ref
        p, c = lltype.parentlink(self.value)
        assert p is None, "child arrays are NOT needed by rtyper"

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
    
class StrArrayNode(ArrayNode):
    printables = dict([(ord(i), None) for i in
      ("0123456789abcdefghijklmnopqrstuvwxyz" +
       "ABCDEFGHIJKLMNOPQRSTUVWXYZ" +
       "!#$%&()*+,-./:;<=>?@[\\]^_`{|}~ '")])

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

    def __init__(self, db, value):
        assert isinstance(lltype.typeOf(value), lltype.Array)
        self.db = db
        self.ref = self.make_ref('%arrayinstance', '')
        self.value = value

    def constantvalue(self):
        return "{ %s } {%s %s}" % (self.db.get_machine_word(),
                                   self.db.get_machine_word(),
                                   len(self.value.items))

