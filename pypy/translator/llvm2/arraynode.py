import py
from pypy.rpython import lltype
from pypy.translator.llvm2.log import log
from pypy.translator.llvm2.node import LLVMNode
from pypy.objspace.flow.model import Constant
import itertools  
log = log.structnode

count = itertools.count().next 

def wrapstr(s):
    return '"%s"' % s

class ArrayTypeNode(LLVMNode):
    _issetup = False
    def __init__(self, db, array):
        self.db = db
        assert isinstance(array, lltype.Array)
        self.array = array
        c = count()
        ref_template = wrapstr("%%array.%s." + str(c))

        self.ref = ref_template % array.OF
        self.constructor_ref = wrapstr("%%new.array.%s" % c)
        self.constructor_decl = "%s * %s(int %%len)" % \
                                (self.ref, self.constructor_ref)

    def __str__(self):
        return "<ArrayTypeNode %r>" % self.ref
        
    def writedecl(self, codewriter): 
        # declaration for constructor
        codewriter.declare(self.constructor_decl)

    def writeimpl(self, codewriter):
        """ this function generates a LLVM function like the following:
        %array = type { int, [0 x double] }
        %array *%NewArray(int %len) {
           ;; Get the offset of the 'len' element of the array from the null
           ;; pointer.
           %size = getelementptr %array* null, int 0, uint 1, %int %len
           %usize = cast double* %size to uint
           %ptr = malloc sbyte, uint %usize
           %result = cast sbyte* %ptr to %array*
           %arraylength = getelementptr %array* %result, int 0, uint 0
           store int %len, int* %arraylength 
           ret %array* %result
        }"""
        from pypy.translator.llvm2.atomic import is_atomic

        log.writeimpl(self.ref)
        codewriter.openfunc(self.constructor_decl)
        indices = [("uint", 1), ("int", "%len")]
        codewriter.getelementptr("%size", self.ref + "*",
                                 "null", *indices)
        fromtype = self.db.repr_arg_type(self.array.OF) 
        codewriter.cast("%usize", fromtype + "*", "%size", "uint")
        codewriter.malloc("%ptr", "sbyte", "%usize", atomic=is_atomic(self))
        codewriter.cast("%result", "sbyte*", "%ptr", self.ref+"*")
        codewriter.getelementptr("%arraylength", self.ref+"*", "%result", ("uint", 0))
        codewriter.store("int", "%len", "%arraylength")
        codewriter.ret(self.ref+"*", "%result")
        codewriter.closefunc()

    def setup(self):
        self.db.prepare_repr_arg_type(self.array.OF)
        self._issetup = True

    # ______________________________________________________________________
    # entry points from genllvm
    #
    def writedatatypedecl(self, codewriter):
        codewriter.arraydef(self.ref, self.db.repr_arg_type(self.array.OF))

# Each ArrayNode is a global constant.  This needs to have a specific type of
# a certain type.

class ArrayNode(LLVMNode):

    _issetup = False 
    array_counter = 0

    def __init__(self, db, value):
        self.db = db
        name = '"%%arrayinstance.%s.%s"' % (value._TYPE.OF, ArrayNode.array_counter)
        self.ref = name
        self.value = value
        ArrayNode.array_counter += 1

    def __str__(self):
        return "<ArrayNode %r>" %(self.ref,)

    def setup(self):
        T = self.value._TYPE.OF
        for item in self.value.items:
            if not isinstance(T, lltype.Primitive):
                # Create a dummy constant hack XXX
                c = Constant(item, T)
                self.db.prepare_arg(c)

        self._issetup = True

    def getall(self):
        arraylen = len(self.value.items)

        res = []

        T = self.value._TYPE.OF
        typval = self.db.repr_arg_type(self.value._TYPE.OF)
        for value in self.value.items:
            if not isinstance(T, lltype.Primitive):
                # Create a dummy constant hack XXX
                value = self.db.repr_arg(Constant(value, T))
            else:
                value = repr(value)
            res.append((typval, value))

        arrayvalues = ", ".join(["%s %s" % (t, v) for t, v in res])

        type_ = "{ int, [%s x %s] }" % (len(self.value.items),
                                        self.db.repr_arg_type(self.value._TYPE.OF))
        
        value = "int %s, [%s x %s] [ %s ]" % (arraylen,
                                              arraylen,
                                              typval,
                                              arrayvalues)
        return type_, value
    
    def writeglobalconstants(self, codewriter):
        type_, values = self.getall()
        codewriter.globalinstance(self.ref, type_, values)
