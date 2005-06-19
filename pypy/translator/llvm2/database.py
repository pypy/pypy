from pypy.translator.llvm2.log import log 
from pypy.translator.llvm2.funcnode import FuncNode
from pypy.rpython import lltype
from pypy.objspace.flow.model import Block, Constant, Variable

log = log.database 

PRIMITIVES_TO_LLVM = {lltype.Signed: "int",
                      lltype.Bool: "bool"}

class Database(object): 
    def __init__(self, translator): 
        self._translator = translator
        self.obj2node = {}
        self._pendingsetup = []

    def prepare_repr_arg(self, const_or_var):
        if const_or_var in self.obj2node:
            return
        if isinstance(const_or_var, Constant):
            if isinstance(const_or_var.concretetype, lltype.Primitive):
                pass
            else:
                node = FuncNode(self, const_or_var) 
                self.obj2node[const_or_var] = node
                log("added to pending nodes:", node) 
                self._pendingsetup.append(node) 

    def prepare_repr_arg_type(self, type_):
        if not isinstance(type_, lltype.Primitive):
            log.XXX("need to prepare typeref")

    def prepare_arg(self, const_or_var):
        log.prepare(const_or_var)
        self.prepare_repr_arg(const_or_var)
        self.prepare_repr_arg_type(const_or_var.concretetype)
            
    def process(self):
        if self._pendingsetup: 
            self._pendingsetup.pop().setup()
        return bool(self._pendingsetup) 

    def getobjects(self): 
        return self.obj2node.values()

    def repr_arg(self, arg):
        if (isinstance(arg, Constant) and 
            isinstance(arg.concretetype, lltype.Primitive)):
            return str(arg.value).lower() #False --> false
        elif isinstance(arg, Variable):
            return "%" + str(arg)
        return self.obj2node[arg].ref

    def repr_arg_type(self, arg):
        return PRIMITIVES_TO_LLVM[arg.concretetype]

    def repr_arg_multi(self, args):
        return [self.repr_arg(arg) for arg in args]

    def repr_arg_type_multi(self, args):
        return [self.repr_arg_type(arg) for arg in args]
