from pypy.translator.js.node import LLVMNode, ConstantLLVMNode
from pypy.rpython.lltypesystem import lltype


class OpaqueNode(ConstantLLVMNode):
    def __init__(self, db, value):
        self.db = db
        self.value = value
        self.ref = "null"
    # ______________________________________________________________________
    # main entry points from genllvm 

    def writeglobalconstants(self, codewriter):
        # XXX Dummy - not sure what what we want
        pass
