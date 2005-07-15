import py
from pypy.rpython import lltype
from pypy.translator.llvm2.log import log
from pypy.translator.llvm2.node import LLVMNode, ConstantLLVMNode
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
        self.arraytype = array.OF
        # ref is used to reference the arraytype in llvm source 
        # constructor_ref is used to reference the constructor 
        # for the array type in llvm source code 
        # constructor_decl is used to declare the constructor
        # for the array type (see writeimpl)
        c = nextnum()
        self.ref = "%%array.%s.%s" % (c, self.arraytype)
        self.constructor_ref = "%%new.array.%s" % c 
        self.constructor_decl = "%s * %s(int %%len)" % \
                                (self.ref, self.constructor_ref)

    def __str__(self):
        return "<ArrayTypeNode %r>" % self.ref
        
    def setup(self):
        self.db.prepare_repr_arg_type(self.arraytype)
        self._issetup = True

    # ______________________________________________________________________
    # entry points from genllvm
    #
    def writedatatypedecl(self, codewriter):
        codewriter.arraydef(self.ref, self.db.repr_arg_type(self.arraytype))

    def writedecl(self, codewriter): 
        # declaration for constructor
        codewriter.declare(self.constructor_decl)

    def writeimpl(self, codewriter):
        log.writeimpl(self.ref)
        fromtype = self.db.repr_arg_type(self.arraytype) 
        varsize.write_constructor(codewriter, self.ref, 
                                  self.constructor_decl,
                                  fromtype)

class ArrayNode(ConstantLLVMNode):
    """ An arraynode.  Elements can be
    a primitive,
    a struct,
    pointer to struct/array
    """
    _issetup = True 
    def __init__(self, db, value):
        assert isinstance(lltype.typeOf(value), lltype.Array)
        self.db = db
        self.value = value
        self.arraytype = lltype.typeOf(value).OF
        self.ref = "%%arrayinstance.%s" % (nextnum(),)

    def __str__(self):
        return "<ArrayNode %r>" % (self.ref,)

    def setup(self):
        if isinstance(self.arraytype, lltype.Ptr):
            for item in self.value.items:
                self.db.prepare_ptr(item)

        # set castref (note we must ensure that types are "setup" before we can
        # get typeval)
        typeval = self.db.repr_arg_type(lltype.typeOf(self.value))
        self.castref = "cast (%s* %s to %s*)" % (self.get_typerepr(),
                                                 self.ref,
                                                 typeval)
        self._issetup = True

    def get_typerepr(self):
        items = self.value.items
        arraylen = len(items)
        typeval = self.db.repr_arg_type(self.arraytype)
        return "{ int, [%s x %s] }" % (arraylen, typeval)

    def castfrom(self):
        return "%s*" % self.get_typerepr()
    
    def constantvalue(self):
        """ Returns the constant representation for this node. """
        items = self.value.items
        arraylen = len(items)
        typeval = self.db.repr_arg_type(self.arraytype)

        arrayvalues = [self.db.repr_constant(v)[1] for v in items]
        value = "int %s, [%s x %s] [ %s ]" % (arraylen,
                                              arraylen,
                                              typeval,
                                              ", ".join(arrayvalues))

        return "%s {%s}" % (self.get_typerepr(), value)
    
    # ______________________________________________________________________
    # entry points from genllvm

    def writeglobalconstants(self, codewriter):
        codewriter.globalinstance(self.ref, self.constantvalue())
