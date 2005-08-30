import py
from pypy.translator.llvm.node import ConstantLLVMNode
from pypy.translator.llvm.log import log 
log = log.extfuncnode

class ExternalFuncNode(ConstantLLVMNode):
    used_external_functions = {}

    def __init__(self, db, value):
        self.db = db
        self.value = value
        name = value._callable.__name__
        assert name.startswith("ll")
        name = "LL" + name[2:] 
        self.ref = self.make_ref("%", name)
        self.used_external_functions[self.ref] = True

    def getdecl(self):
        T = self.value._TYPE
        args = [self.db.repr_type(a) for a in T.ARGS]
        decl = "%s %s(%s)" % (self.db.repr_type(T.RESULT),
                              self.ref,
                              ", ".join(args))
        return decl

    def writedecl(self, codewriter): 
        codewriter.declare(self.getdecl())

    #def writeimpl(self, codewriter): 
    #    self.used_external_functions[self.ref] = True

    def writeglobalconstants(self, codewriter):
        pass
