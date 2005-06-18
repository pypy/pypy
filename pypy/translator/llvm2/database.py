from pypy.translator.llvm2.log import log 
from pypy.translator.llvm2.funcnode import FuncNode
from pypy.rpython import lltype
from pypy.objspace.flow.model import Block, Constant, Variable

log = log.database 

PRIMITIVES_TO_LLVM = {lltype.Signed: "int"}

class Database(object): 
    def __init__(self, translator): 
        self._translator = translator
        self.obj2node = {}   
        self._pendingsetup = []

    def getgraph(self, func): 
        return self._translator.flowgraphs[func] 

    def getnode(self, obj): 
        assert hasattr(obj, 'func_code')
        try:
            return self.obj2node[obj]
        except KeyError: 
            node = FuncNode(self, obj) 
            self.obj2node[obj] = node
            log("add pending setup", node.ref) 
            self._pendingsetup.append(node) 
            return node 

    def process(self): 
        if self._pendingsetup: 
            self._pendingsetup.pop().setup()
        return bool(self._pendingsetup) 

    def getobjects(self): 
        return self.obj2node.values()

    def getref(self, arg):
        if isinstance(arg, Constant):
            if isinstance(arg.concretetype, lltype.Primitive):
                return str(arg.value).lower() #False --> false
            raise TypeError, "can't handle the Constant %s" % arg
        elif isinstance(arg, Variable):
            return "%" + str(arg)
        else:
            raise TypeError, arg

    def gettyperef(self, arg):
        return PRIMITIVES_TO_LLVM[arg.concretetype]

    def multi_getref(self, args):
        return [self.getref(arg) for arg in args]

    def multi_gettyperef(self, args):
        return [self.gettyperef(arg) for arg in args]
