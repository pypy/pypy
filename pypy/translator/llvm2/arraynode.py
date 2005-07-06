import py
from pypy.rpython import lltype
from pypy.translator.llvm2.log import log
from pypy.translator.llvm2.node import LLVMNode
from pypy.translator.llvm2 import varsize 
import itertools  
log = log.structnode

nextnum = itertools.count().next 

class ArrayTypeNode(LLVMNode):
    _issetup = False
    def __init__(self, db, array):
        assert isinstance(array, lltype.Array)

        self.db = db
        self.array = array

        # ref is used to reference the arraytype in llvm source 
        # constructor_ref is used to reference the constructor 
        # for the array type in llvm source code 
        # constructor_decl is used to declare the constructor
        # for the array type (see writeimpl)
        c = nextnum()
        self.ref = "%%array.%s.%s" % (c, array.OF)
        self.constructor_ref = "%%new.array.%s" % c 
        self.constructor_decl = "%s * %s(int %%len)" % \
                                (self.ref, self.constructor_ref)

    def __str__(self):
        return "<ArrayTypeNode %r>" % self.ref
        
    def setup(self):
        self.db.prepare_repr_arg_type(self.array.OF)
        self._issetup = True

    # ______________________________________________________________________
    # entry points from genllvm
    #
    def writedatatypedecl(self, codewriter):
        codewriter.arraydef(self.ref, self.db.repr_arg_type(self.array.OF))

    def writedecl(self, codewriter): 
        # declaration for constructor
        codewriter.declare(self.constructor_decl)

    def writeimpl(self, codewriter):
        log.writeimpl(self.ref)
        fromtype = self.db.repr_arg_type(self.array.OF) 
        varsize.write_constructor(codewriter, self.ref, 
                                  self.constructor_decl,
                                  fromtype)

class ArrayNode(LLVMNode):
    _issetup = True 
    def __init__(self, db, value):
        assert isinstance(lltype.typeOf(value), lltype.Array)
        self.db = db
        self.value = value
        self.arraytype = lltype.typeOf(value).OF
        self.ref = "%%arrayinstance.%s.%s" % (self.arraytype, nextnum())
        if isinstance(self.arraytype, lltype.Ptr):
            for item in self.value.items:
                self.db.addptrvalue(item)

    def __str__(self):
        return "<ArrayNode %r>" %(self.ref,)
    
    def typeandvalue(self):
        """ Returns the type and value for this node. """
        items = self.value.items
        arraylen = len(items)

        typeval = self.db.repr_arg_type(self.arraytype)

        type_ = "{ int, [%s x %s] }" % (arraylen, typeval)        
        arrayvalues = ["%s %s" % self.db.reprs_constant(v) for v in items]
        value = "int %s, [%s x %s] [ %s ]" % (arraylen,
                                              arraylen,
                                              typeval,
                                              ", ".join(arrayvalues))
        return type_, value
    
    # ______________________________________________________________________
    # entry points from genllvm

    def writeglobalconstants(self, codewriter):
        type_, values = self.typeandvalue()
        codewriter.globalinstance(self.ref, type_, values)
