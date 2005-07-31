import py
from pypy.rpython import lltype
from pypy.translator.llvm2.log import log
from pypy.translator.llvm2.node import LLVMNode, ConstantLLVMNode
from pypy.translator.llvm2 import varsize 
import itertools
log = log.structnode

nextnum = itertools.count().next

class ArrayTypeNode(LLVMNode):
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
        self.ref = "%%arraytype.%s.%s" % (c, self.arraytype)
        self.constructor_ref = "%%new.array.%s" % c
        self.constructor_decl = "%s * %s(int %%len)" % \
                                (self.ref, self.constructor_ref)

    def __str__(self):
        return "<ArrayTypeNode %r>" % self.ref
        
    def setup(self):
        self.db.prepare_repr_arg_type(self.arraytype)

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

class VoidArrayTypeNode(LLVMNode):

    def __init__(self, db, array):
        assert isinstance(array, lltype.Array)
        self.ref = "%arraytype.Void"

    def writedatatypedecl(self, codewriter):
        td = "%s = type { int }" % self.ref
        codewriter.append(td)
        
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

    def get_arrayvalues(self):
        items = self.value.items
        return [self.db.repr_constant(v)[1] for v in items]

    def get_typerepr(self):
        arraylen = len(self.get_arrayvalues())
        typeval = self.db.repr_arg_type(self.arraytype)
        return "{ int, [%s x %s] }" % (arraylen, typeval)

    def get_ref(self):
        """ Returns a reference as used for operations in blocks. """        
        typeval = self.db.repr_arg_type(lltype.typeOf(self.value))
        ref = "cast (%s* %s to %s*)" % (self.get_typerepr(),
                                        self.ref,
                                        typeval)

        p, c = lltype.parentlink(self.value)
        if p is not None:
            assert False, "XXX TODO"
        return ref

    def get_pbcref(self, toptr):
        """ Returns a reference as a pointer used per pbc. """        
        ref = self.ref
        p, c = lltype.parentlink(self.value)
        if p is not None:
            assert False, "XXX TODO"

        fromptr = "%s*" % self.get_typerepr()
        refptr = "getelementptr (%s %s, int 0)" % (fromptr, ref)
        ref = "cast(%s %s to %s)" % (fromptr, refptr, toptr)
        return ref

    def get_childref(self, index):
        return "getelementptr(%s* %s, int 0, uint 1, int %s)" %(
            self.get_typerepr(),
            self.ref,
            index)
    
    def constantvalue(self):
        """ Returns the constant representation for this node. """
        arrayvalues = self.get_arrayvalues()
        typeval = self.db.repr_arg_type(self.arraytype)

        # first length is logical, second is physical
        value = "int %s, [%s x %s] [ %s ]" % (self.get_length(),
                                              len(arrayvalues),
                                              typeval,
                                              ", ".join(arrayvalues))

        s = "%s {%s}" % (self.get_typerepr(), value)

        #XXXX ????????
        #XXX this does not work for arrays inlined in struct. How else to do this?
        #if typeval == 'sbyte':  #give more feedback for strings
        #    limited_printable = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ/-.'
        #    s += ' ;"'
        #    for item in items:
        #        if item in limited_printable:
        #            s += item
        #        else:
        #            s += '_'
        #    s += '" '
        return s
    
    # ______________________________________________________________________
    # entry points from genllvm

    def writeglobalconstants(self, codewriter):
        p, c = lltype.parentlink(self.value)
        if p is None:
            codewriter.globalinstance(self.ref, self.constantvalue())

class StrArrayNode(ArrayNode):

    def get_arrayvalues(self):
        items = self.value.items
        if len(items) == 0 or items[-1] != chr(0):
            items = items + [chr(0)]
        return [self.db.repr_constant(v)[1] for v in items]

class VoidArrayNode(ConstantLLVMNode):

    def __init__(self, db, value):
        assert isinstance(lltype.typeOf(value), lltype.Array)
        self.ref = self.make_ref('%arrayinstance', '')
        self.value = value

    def get_length(self):
        """ returns logical length of array """
        items = self.value.items
        return len(items)

    def get_typerepr(self):
        return "{ int }"

    def get_arrayvalues(self):
        return []

    def constantvalue(self):
        value = "int %s" % (self.get_length(),)
        s = "%s {%s}" % (self.get_typerepr(), value)
        return s
    
    def writeglobalconstants(self, codewriter):
        p, c = lltype.parentlink(self.value)
        if p is None:
            codewriter.globalinstance(self.ref, self.constantvalue())
