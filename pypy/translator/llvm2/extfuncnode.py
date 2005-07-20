import py
from pypy.objspace.flow.model import Block, Constant, Variable, Link
from pypy.objspace.flow.model import flatten, mkentrymap, traverse
from pypy.rpython import lltype
from pypy.translator.backendoptimization import remove_same_as 
from pypy.translator.unsimplify import remove_double_links                     
from pypy.translator.llvm2.node import LLVMNode, ConstantLLVMNode
from pypy.translator.llvm2.atomic import is_atomic
from pypy.translator.llvm2.log import log 
from pypy.rpython.extfunctable import table as extfunctable
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
