from pypy.translator.llvm2.node import LLVMNode, ConstantLLVMNode
from pypy.rpython import lltype

class OpaqueTypeNode(LLVMNode):

    def __init__(self, db, opaquetype): 
        assert isinstance(opaquetype, lltype.OpaqueType)
        self.db = db
        self.opaquetype = opaquetype
        self.ref = "%%opaque.%s" % (opaquetype.tag)
        
    def __str__(self):
        return "<OpaqueNode %r>" %(self.ref,)

    # ______________________________________________________________________
    # main entry points from genllvm 

    def writedatatypedecl(self, codewriter):
        # XXX Dummy - not sure what what we want
        codewriter.funcdef(self.ref, 'sbyte*', ['sbyte *'])


class OpaqueNode(ConstantLLVMNode):
    def __init__(self, db, value):
        self.db = db
        self.value = value
        self.ref = "null"
