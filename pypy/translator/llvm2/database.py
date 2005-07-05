from pypy.translator.llvm2.log import log 
from pypy.translator.llvm2.funcnode import FuncNode, FuncTypeNode
from pypy.translator.llvm2.structnode import StructNode, StructVarsizeNode, \
     StructTypeNode, StructVarsizeTypeNode
from pypy.translator.llvm2.arraynode import ArrayNode, ArrayTypeNode
from pypy.rpython import lltype
from pypy.objspace.flow.model import Block, Constant, Variable

log = log.database 

PRIMITIVES_TO_LLVM = {lltype.Signed: "int",
                      lltype.Char: "sbyte",
                      lltype.Unsigned: "uint",
                      lltype.Bool: "bool",
                      lltype.Float: "double",
                      lltype.Void: "void"}

class NormalizingDict(object): 
    """ this is a helper dict for obj2node in order 
        to allow saner key-unification for Ptrs to functions 
        (and possibly other stuff in the future)
    """ 
    def __init__(self): 
        self._dict = {}
    def __repr__(self): 
        return repr(self._dict)
    def dump(self): 
        for x,y in self._dict.items():
            print x, y
    def _get(self, key): 
        if isinstance(key, Constant): 
            if isinstance(key.value, lltype._ptr): 
                key = key.value._obj 
        return key 
    def __getitem__(self, key): 
        key = self._get(key)
        return self._dict[key]
    def __contains__(self, key): 
        key = self._get(key)
        return key in self._dict 
    def __setitem__(self, key, value): 
        key = self._get(key)
        self._dict[key] = value 
    def __delitem__(self, key): 
        key = self._get(key)
        del self._dict[key]
    def values(self): 
        return self._dict.values()
    def items(self): 
        return self._dict.items()

class Database(object): 
    def __init__(self, translator): 
        self._translator = translator
        self.obj2node = NormalizingDict() 
        self._pendingsetup = []
        self._tmpcount = 1
        
    def addpending(self, key, node): 
        assert key not in self.obj2node, (
            "node with key %r already known!" %(key,))
        self.obj2node[key] = node 
        log("added to pending nodes:", node) 
        self._pendingsetup.append(node) 

    def prepare_repr_arg(self, const_or_var):
        """if const_or_var is not already in a dictionary self.obj2node,
        the appropriate node gets constructed and gets added to
        self._pendingsetup and to self.obj2node"""
        if const_or_var in self.obj2node:
            return
        if isinstance(const_or_var, Constant):
            
            ct = const_or_var.concretetype
            while isinstance(ct, lltype.Ptr):
                ct = ct.TO
            
            if isinstance(ct, lltype.FuncType):
                self.addpending(const_or_var, FuncNode(self, const_or_var))
            else:
                value = const_or_var.value
                while hasattr(value, "_obj"):
                    value = value._obj

                if isinstance(ct, lltype.Struct):
                    if ct._arrayfld:
                        self.addpending(const_or_var, StructVarsizeNode(self, value))
                    else:
                        self.addpending(const_or_var, StructNode(self, value))

                elif isinstance(ct, lltype.Array):
                    self.addpending(const_or_var, ArrayNode(self, value))

                elif isinstance(ct, lltype.Primitive):
                    log.prepare(const_or_var, "(is primitive)")
                else:
                    log.XXX("not sure what to do about %s(%s)" % (ct, const_or_var))
        else:
            log.prepare(const_or_var, type(const_or_var)) #XXX dont checkin

    def prepare_repr_arg_multi(self, args):
        for const_or_var in args:
            self.prepare_repr_arg(const_or_var)

    def prepare_repr_arg_type(self, type_):
        if type_ in self.obj2node:
            return
        if isinstance(type_, lltype.Primitive):
            pass
        elif isinstance(type_, lltype.Ptr): 
            self.prepare_repr_arg_type(type_.TO)

        elif isinstance(type_, lltype.Struct):
            if type_._arrayfld:
                self.addpending(type_, StructVarsizeTypeNode(self, type_))
            else:
                self.addpending(type_, StructTypeNode(self, type_))                
        elif isinstance(type_, lltype.FuncType): 
            self.addpending(type_, FuncTypeNode(self, type_))

        elif isinstance(type_, lltype.Array): 
            self.addpending(type_, ArrayTypeNode(self, type_))

        else:     
            log.XXX("need to prepare typerepr", type_)

    def prepare_repr_arg_type_multi(self, types):
        for type_ in types:
            self.prepare_repr_arg_type(type_)

    def prepare_arg(self, const_or_var):
        log.prepare(const_or_var)
        self.prepare_repr_arg_type(const_or_var.concretetype)
        self.prepare_repr_arg(const_or_var)
            
    def setup_all(self):
        while self._pendingsetup: 
            x = self._pendingsetup.pop()
            log.setup_all(x)
            x.setup()

    def getobjects(self, subset_types=None):
        res = []
        for v in self.obj2node.values():
            if subset_types is None or isinstance(v, subset_types):
                res.append(v)
        return res
        
    # __________________________________________________________
    # Representing variables and constants in LLVM source code 
    
    def repr_arg(self, arg):
        if (isinstance(arg, Constant) and 
            isinstance(arg.concretetype, lltype.Primitive)):
           
            # XXX generalize and test this 
            if isinstance(arg.value, str) and len(arg.value) == 1: 
                return str(ord(arg.value))
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
