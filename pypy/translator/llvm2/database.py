from pypy.translator.llvm2.log import log 
from pypy.translator.llvm2.funcnode import FuncNode
from pypy.translator.llvm2.structnode import StructNode 
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
        self._tmpcount = 1

    def addpending(self, key, node): 
        assert key not in self.obj2node, (
            "node with key %r already known!" %(key,))
        self.obj2node[key] = node 
        log("added to pending nodes:", node) 
        self._pendingsetup.append(node) 

    def prepare_repr_arg(self, const_or_var):
        if const_or_var in self.obj2node:
            return
        if isinstance(const_or_var, Constant):
            if isinstance(const_or_var.concretetype, lltype.Primitive):
                pass
                #log.prepare(const_or_var, "(is primitive)") 
            else:
                self.addpending(const_or_var, FuncNode(self, const_or_var)) 
        else:
            log.prepare.ignore(const_or_var) 

    def prepare_repr_arg_type(self, type_):
        if type_ in self.obj2node:
            return
        if isinstance(type_, lltype.Primitive):
            pass
        elif isinstance(type_, lltype.Ptr): 
            self.prepare_repr_arg_type(type_.TO)
        elif isinstance(type_, lltype.Struct): 
            self.addpending(type_, StructNode(self, type_))
        else:     
            log.XXX("need to prepare typerepr", type_)

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
        if isinstance(arg, (Constant, Variable)): 
            arg = arg.concretetype 
        try:
            return self.obj2node[arg].ref 
        except KeyError: 
            if isinstance(arg, lltype.Primitive):
                return PRIMITIVES_TO_LLVM[arg]
            elif isinstance(arg, lltype.Ptr):
                return self.repr_arg_type(arg.TO) + '*'
            else: 
                raise TypeError("cannot represent %r" %(arg,))

    def repr_arg_multi(self, args):
        return [self.repr_arg(arg) for arg in args]

    def repr_arg_type_multi(self, args):
        return [self.repr_arg_type(arg) for arg in args]

    def repr_tmpvar(self): 
        count = self._tmpcount 
        self._tmpcount += 1
        return "%tmp." + str(count) 
        
