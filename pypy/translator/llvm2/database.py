import sys
from pypy.translator.llvm2.log import log 
from pypy.translator.llvm2.funcnode import FuncNode, FuncTypeNode
from pypy.translator.llvm2.extfuncnode import ExternalFuncNode
from pypy.translator.llvm2.structnode import StructNode, StructVarsizeNode, \
     StructTypeNode, StructVarsizeTypeNode
from pypy.translator.llvm2.arraynode import ArrayNode, StrArrayNode, \
     VoidArrayNode, ArrayTypeNode, VoidArrayTypeNode
from pypy.translator.llvm2.opaquenode import OpaqueNode, OpaqueTypeNode
from pypy.translator.llvm2.node import ConstantLLVMNode
from pypy.rpython import lltype
from pypy.objspace.flow.model import Block, Constant, Variable
from pypy.rpython.rstr import STR
            
log = log.database 

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
        r = ""
        for x,y in self._dict.items():
            r += "%s -> %s" % (x, y)
        return r
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
    def get(self, key):
        key = self._get(key)
        return self._dict.get(key)
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

        # debug operation comments
        self._opcomments = {}

        self.primitives_init()

    def primitives_init(self):
        primitives = {
            lltype.Char: "sbyte",
            lltype.Bool: "bool",
            lltype.Float: "double",
            lltype.UniChar: "uint",
            lltype.Void: "void"}

        # 32 bit platform
        if sys.maxint == 2**31-1:
            primitives.update({
                lltype.Signed: "int",
                lltype.Unsigned: "uint" })
            
        # 64 bit platform
        elif sys.maxint == 2**63-1:        
            primitives.update({
                lltype.Signed: "long",
                lltype.Unsigned: "ulong" })
            
        else:
            assert False, "Unsupported platform"        

        self.primitives = primitives
        
    #_______for debugging llvm code_________________________

    def add_op2comment(self, lenofopstr, op):
        """ internal method for adding comments on each operation """
        tmpname = self.repr_tmpvar() + ".comment"
        self._opcomments[op] = (lenofopstr, tmpname)
        return tmpname
        
    def get_op2comment(self, op):
        """ internal method for adding comments on each operation """
        return self._opcomments.get(op, None)
    
    #_______debuggging______________________________________

    def dump_pbcs(self):
        r = ""
        for k, v in self.obj2node.items():
            
            if (isinstance(k, lltype.LowLevelType) or
                isinstance(k, Constant)):
                continue

            assert isinstance(lltype.typeOf(k), lltype.ContainerType)
            # Only dump top levels
            p, _ = lltype.parentlink(k)
            if p is None:
                ref = v.get_ref()
                pbc_ref = v.get_ref()
                
                r += "\ndump_pbcs %s (%s)\n" \
                     "getref -> %s \n" \
                     "pbcref -> %s \n" % (v, k, ref, pbc_ref)
            return r
    
    #_______create node_____________________________________

    def create_constant_node(self, type_, value):
        node = None
        if isinstance(type_, lltype.FuncType):
            if getattr(value._callable, "suggested_primitive", False):
                node = ExternalFuncNode(self, value)
            else:
                node = FuncNode(self, value)

        elif isinstance(type_, lltype.Struct):
            if type_._arrayfld:
                node = StructVarsizeNode(self, value)
            else:
                node = StructNode(self, value)
                    
        elif isinstance(type_, lltype.Array):
            if type_.OF is lltype.Char:
                node = StrArrayNode(self, value)
            elif type_.OF is lltype.Void:
                node = VoidArrayNode(self, value)
            else:
                node = ArrayNode(self, value)

        elif isinstance(type_, lltype.OpaqueType):
            node = OpaqueNode(self, value)

        assert node is not None, "%s not supported" % (type_)
        return node

    def addpending(self, key, node):
        # santity check we at least have a key of the right type
        assert (isinstance(key, lltype.LowLevelType) or
                isinstance(key, Constant) or
                isinstance(lltype.typeOf(key), lltype.ContainerType))

        assert key not in self.obj2node, (
            "node with key %r already known!" %(key,))
        
        log("added to pending nodes:", type(key), node)        
        self.obj2node[key] = node 
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

            # Only prepare root values at this point 
            if isinstance(ct, lltype.Array) or isinstance(ct, lltype.Struct):
                p, c = lltype.parentlink(value)
                if p is None:
                    log.prepare_repr_arg("skipping preparing non root", value)
                    return

            if value is not None:
                self.addpending(const_or_var, self.create_constant_node(ct.TO, value))
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
            if type_.OF is lltype.Void:
                self.addpending(type_, VoidArrayTypeNode(self, type_))
            else:
                self.addpending(type_, ArrayTypeNode(self, type_))

        elif isinstance(type_, lltype.OpaqueType):
            self.addpending(type_, OpaqueTypeNode(self, type_))            

        else:
            assert False, "need to prepare typerepr %s %s" % (type_, type(type_))

    def prepare_repr_arg_type_multi(self, types):
        for type_ in types:
            self.prepare_repr_arg_type(type_)

    def prepare_arg(self, const_or_var):
        log.prepare(const_or_var)
        self.prepare_repr_arg_type(const_or_var.concretetype)
        self.prepare_repr_arg(const_or_var)

    def prepare_constant(self, type_, value):
        if isinstance(type_, lltype.Primitive):
            #log.prepare_constant(value, "(is primitive)")
            return
        
        if isinstance(type_, lltype.Ptr):        
            
            type_ = type_.TO
            value = value._obj

            log.prepare_constant("preparing ptr", value)

            # we dont need a node for nulls
            if value is None:
                return

        # we can share data via pointers
        if value not in self.obj2node: 
            self.addpending(value, self.create_constant_node(type_, value))

        # Always add type (it is safe)
        self.prepare_repr_arg_type(type_)
        
    def setup_all(self, entrynode):
        # Constants setup need to be done after the rest
        self.entrynode = entrynode
        while self._pendingsetup: 
            node = self._pendingsetup.pop()
            log.settingup(node)
            node.setup()

    def getnodes(self):
        return self.obj2node.values()
        
    # __________________________________________________________
    # Representing variables and constants in LLVM source code 

    def repr_arg(self, arg):
        if isinstance(arg, Constant):
            if isinstance(arg.concretetype, lltype.Primitive):
                return self.primitive_to_str(arg.concretetype, arg.value)
            else:
                node = self.obj2node.get(arg)
                if node is None:
                    return 'null'
                else:
                    return node.get_ref()
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
                return self.primitives[arg]
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

    def repr_constant(self, value):
        " returns node and repr as tuple "
        type_ = lltype.typeOf(value)
        if isinstance(type_, lltype.Primitive):
            repr = self.primitive_to_str(type_, value)
            return None, "%s %s" % (self.repr_arg_type(type_), repr)

        elif isinstance(type_, lltype.Ptr):
            toptr = self.repr_arg_type(type_)
            value = value._obj

            # special case, null pointer
            if value is None:
                return None, "%s null" % (toptr,)

            node = self.obj2node[value]
            ref = node.get_pbcref(toptr)
            return node, "%s %s" % (toptr, ref)

        elif isinstance(type_, lltype.Array) or isinstance(type_, lltype.Struct):
            node = self.obj2node[value]
            return node, node.constantvalue()

        assert False, "%s not supported" % (type(value))

    def repr_tmpvar(self): 
        count = self._tmpcount 
        self._tmpcount += 1
        return "%tmp." + str(count) 

    # __________________________________________________________
    # Primitive stuff

    def float_to_str(self, value):
        repr = "%f" % value
        # llvm requires a . when using e notation
        if "e" in repr and "." not in repr:
            repr = repr.replace("e", ".0e")
        elif repr in ["inf", "nan"]:
            # Need hex repr
            import struct
            packed = struct.pack("d", value)                
            repr = "0x" + "".join([("%02x" % ord(ii)) for ii in packed])
        return repr
    
    def primitive_to_str(self, type_, value):
        if type_ is lltype.Bool:
            repr = str(value).lower() #False --> false
        elif type_ is lltype.Char:
            repr = str(ord(value))
        elif type_ is lltype.UniChar:
            repr = str(ord(value))
        elif type_ is lltype.Float:
            repr = self.float_to_str(value)
        else:
            repr = str(value)
        return repr

    def get_machine_word(self):
        return self.primitives[lltype.Signed]

    def get_machine_uword(self):
        return self.primitives[lltype.Unsigned]

    # __________________________________________________________
    # Other helpers

    def is_function_ptr(self, arg):
        if isinstance(arg, (Constant, Variable)): 
            arg = arg.concretetype 
            if isinstance(arg, lltype.Ptr):
                if isinstance(arg.TO, lltype.FuncType):
                    return True
        return False

    def is_atomic(self, value):
        return self.obj2node[value].is_atomic()
