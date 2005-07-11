from pypy.translator.llvm2.log import log 
from pypy.translator.llvm2.funcnode import ExternalFuncNode, FuncNode, FuncTypeNode
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
                      # XXX Preliminary support for unicode, makes sense to
                      # make this more configurable
                      lltype.UniChar: "uint",
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

def primitive_to_str(type_, value):
    if type_ is lltype.Bool:
        repr = str(value).lower() #False --> false
    elif type_ is lltype.Char:
        repr = str(ord(value))
    elif type_ is lltype.UniChar:
        repr = "0" #XXX
    else:
        repr = str(value)
    return repr

class Database(object): 
    def __init__(self, translator): 
        self._translator = translator
        self.obj2node = NormalizingDict() 
        self.ptr2nodevalue = {} 
        self._pendingsetup = []
        self._pendingconstants = []
        self._tmpcount = 1

    def addptrvalue(self, ptrvalue):
        value = ptrvalue._obj
        self.ptr2nodevalue[value] = self.create_constant_node(value, setup=True)        

    def create_constant_node(self, value, setup=False):
        type_ = lltype.typeOf(value)
        node = None
        if isinstance(type_, lltype.FuncType):
            if value._callable and (not hasattr(value, "graph") or value.graph is None 
                                    or getattr(value._callable, "suggested_primitive", False)):
                node = ExternalFuncNode(self, value)
            else:
                node = FuncNode(self, value)

        elif isinstance(type_, lltype.Struct):
            if type_._arrayfld:
                node = StructVarsizeNode(self, value)
            else:
                node = StructNode(self, value)
                    
        elif isinstance(type_, lltype.Array):
            node = ArrayNode(self, value)
        assert node is not None, "%s not supported" % lltype.typeOf(value)
        if setup:
            node.setup()
        return node
        
    def addpending(self, key, node):
        assert key not in self.obj2node, (
            "node with key %r already known!" %(key,))
        self.obj2node[key] = node 
        log("added to pending nodes:", node) 
        if isinstance(node, (StructNode, ArrayNode)):
            self._pendingconstants.append(node)
        else:
            self._pendingsetup.append(node) 

    def prepare_repr_arg(self, const_or_var):
        """if const_or_var is not already in a dictionary self.obj2node,
        the appropriate node gets constructed and gets added to
        self._pendingsetup and to self.obj2node"""
        if const_or_var in self.obj2node:
            return

        if isinstance(const_or_var, Constant):
            ct = const_or_var.concretetype
            if isinstance(ct, lltype.Primitive):
                log.prepare(const_or_var, "(is primitive)")
                return

            assert isinstance(ct, lltype.Ptr), "Preparation of non primitive and non pointer" 
            value = const_or_var.value._obj            
                
            self.addpending(const_or_var, self.create_constant_node(value))
        else:
            log.prepare(const_or_var, type(const_or_var))

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
            assert False, "need to prepare typerepr %s %s" % (type_, type(type_))

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
            log.settingup(x)
            x.setup()

        while self._pendingconstants: 
            x = self._pendingconstants.pop()
            log.settingup_constant(x)
            x.setup()


    def getobjects(self, subset_types=None):
        res = []
        for v in self.obj2node.values() + self.ptr2nodevalue.values():
            if subset_types is None or isinstance(v, subset_types):
                res.append(v)
        return res
        
    # __________________________________________________________
    # Representing variables and constants in LLVM source code 
    
    def repr_arg(self, arg):
        if isinstance(arg, Constant):
            if isinstance(arg.concretetype, lltype.Primitive):
                return primitive_to_str(arg.concretetype, arg.value)
            else:
                node = self.obj2node[arg]
                if hasattr(node, "castref"):
                    return node.castref
                else:
                    return node.ref
        else:
            assert isinstance(arg, Variable)
            return "%" + str(arg)

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

    def repr_argwithtype(self, arg):
        return self.repr_arg(arg), self.repr_arg_type(arg)
            
    def repr_arg_multi(self, args):
        return [self.repr_arg(arg) for arg in args]

    def repr_arg_type_multi(self, args):
        return [self.repr_arg_type(arg) for arg in args]

    def reprs_constant(self, value):
        type_ = lltype.typeOf(value)
        if isinstance(type_, lltype.Primitive):
            repr = primitive_to_str(type_, value)
            return "%s %s" % (self.repr_arg_type(type_), repr)

        elif isinstance(type_, lltype.Ptr):
            node = self.ptr2nodevalue[value._obj]
            ref = node.ref

            fromptr = node.castfrom()
            toptr = self.repr_arg_type(type_)
            if fromptr:
                refptr = "getelementptr (%s %s, int 0)" % (fromptr, ref)
                ref = "cast(%s %s to %s)" % (fromptr, refptr, toptr)
            return "%s %s" % (toptr, ref)

        elif isinstance(type_, lltype.Array) or isinstance(type_, lltype.Struct):
            node = self.create_constant_node(value, setup=True)
            return node.constantvalue()

        assert False, "%s not supported" % (type(value))

    def repr_tmpvar(self): 
        count = self._tmpcount 
        self._tmpcount += 1
        return "%tmp." + str(count) 
