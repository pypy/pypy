import py
from pypy.translator.llvm2.node import LLVMNode
from pypy.translator.llvm2.log import log 
log = log.extfuncnode

class ExternalFuncNode(LLVMNode):

    used_external_functions = {}

    def __init__(self, db, value):
        self.db = db
        self.value = value
        self.ref = "%" + value._callable.__name__

    def setup(self):
        self._issetup = True

    def getdecl(self):
        T = self.value._TYPE
        args = [self.db.repr_arg_type(a) for a in T.ARGS]
        decl = "%s %s(%s)" % (self.db.repr_arg_type(T.RESULT),
                              self.ref,
                              ", ".join(args))
        return decl

    def writedecl(self, codewriter): 
        codewriter.declare(self.getdecl())

    def writeimpl(self, codewriter): 
        self.used_external_functions[self.ref] = True
