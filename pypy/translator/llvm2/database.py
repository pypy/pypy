from pypy.translator.llvm2.log import log 
from pypy.translator.llvm2.funcnode import FuncNode

log = log.database 

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

        
