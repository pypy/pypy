import py
from pypy.rpython import lltype
from pypy.translator.llvm2.log import log
from pypy.translator.llvm2.node import LLVMNode
from pypy.objspace.flow.model import Constant
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
    _issetup = False 
    def __init__(self, db, value):
        self.db = db
        self.value = value
        self.arraytype = value._TYPE.OF
        self.ref = "%%arrayinstance.%s.%s" % (value._TYPE.OF, nextnum())

    def __str__(self):
        return "<ArrayNode %r>" %(self.ref,)

    def setup(self):
        for item in self.value.items:
            if not isinstance(self.arraytype, lltype.Primitive):
                # Create a dummy constant hack XXX
                self.db.prepare_arg(Constant(item, self.arraytype))
        self._issetup = True

    def value_helper(self, value):        
        """ This should really be pushed back to the database??? XXX """
        if not isinstance(self.arraytype, lltype.Primitive):
            # Create a dummy constant hack XXX
            value = self.db.repr_arg(Constant(value, self.arraytype))
        else:
            if isinstance(value, str) and len(value) == 1:
                value = ord(value)                    
            value = str(value)
        return value
    
    def getall(self):
        """ Returns the type and value for this node. """
        items = self.value.items
        typeval = self.db.repr_arg_type(self.arraytype)
        arraylen = len(items)

        type_ = "{ int, [%s x %s] }" % (arraylen, typeval)        
        arrayvalues = ["%s %s" % (typeval,
                                  self.value_helper(v)) for v in items]

        value = "int %s, [%s x %s] [ %s ]" % (arraylen,
                                              arraylen,
                                              typeval,
                                              ", ".join(arrayvalues))
        return type_, value
    
    # ______________________________________________________________________
    # entry points from genllvm

    def writeglobalconstants(self, codewriter):
        type_, values = self.getall()
        codewriter.globalinstance(self.ref, type_, values)
