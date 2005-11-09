
import sys

from pypy.translator.js.funcnode import FuncNode
from pypy.translator.js.structnode import StructNode, StructVarsizeNode
from pypy.translator.js.arraynode import ArrayNode, StrArrayNode, VoidArrayNode
from pypy.translator.js.opaquenode import OpaqueNode
from pypy.rpython.lltypesystem import lltype
from pypy.objspace.flow.model import Constant, Variable
from pypy.translator.js.log import log 
            
log = log.database 

class Database(object): 

    primitives = {
            lltype.Char: "sbyte",
            lltype.Bool: "bool",
            lltype.Float: "double",
            lltype.Signed: "int",
            lltype.Unsigned: "uint",
            lltype.UniChar: "uint",
            lltype.Void: "void"}

    def __init__(self, translator): 
        self.translator = translator
        self.obj2node = {}
        self._pendingsetup = []
        self._tmpcount = 1

    #_______setting up and preperation______________________________

    def create_constant_node(self, type_, value):
        node = None
        if isinstance(type_, lltype.FuncType):
            node = FuncNode(self, value)
            #if getattr(value._callable, "suggested_primitive", False):
            #    node = ExternalFuncNode(self, value)
            #else:
            #    node = FuncNode(self, value)

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
                isinstance(lltype.typeOf(key), lltype.ContainerType))

        assert key not in self.obj2node, (
            "node with key %r already known!" %(key,))
        
        #log("added to pending nodes:", type(key), node)        

        self.obj2node[key] = node 
        self._pendingsetup.append(node)
        
    def prepare_constant(self, type_, value):
        if isinstance(type_, lltype.Primitive):
            #log.prepareconstant(value, "(is primitive)")
            return
        
        if isinstance(type_, lltype.Ptr):        
            
            type_ = type_.TO
            value = value._obj

            #log.prepareconstant("preparing ptr", value)

            # we dont need a node for nulls
            if value is None:
                return

        # we can share data via pointers
        if value not in self.obj2node: 
            self.addpending(value, self.create_constant_node(type_, value))
        
    def prepare_arg_value(self, const_or_var):
        """if const_or_var is not already in a dictionary self.obj2node,
        the appropriate node gets constructed and gets added to
        self._pendingsetup and to self.obj2node"""
        if isinstance(const_or_var, Constant):
            ct = const_or_var.concretetype
            if isinstance(ct, lltype.Primitive):
                #log.prepare(const_or_var, "(is primitive)")
                return

            assert isinstance(ct, lltype.Ptr), "Preparation of non primitive and non pointer" 
            value = const_or_var.value._obj

            # Only prepare root values at this point 
            if isinstance(ct, lltype.Array) or isinstance(ct, lltype.Struct):
                p, c = lltype.parentlink(value)
                if p is None:
                    #log.prepareargvalue("skipping preparing non root", value)
                    return

            if value is not None and value not in self.obj2node:
                self.addpending(value, self.create_constant_node(ct.TO, value))
        else:
            assert isinstance(const_or_var, Variable)


    def prepare_arg(self, const_or_var):
        self.prepare_arg_value(const_or_var)

    def setup_all(self):
        while self._pendingsetup: 
            node = self._pendingsetup.pop()
            #log.settingup(node)
            node.setup()

    def set_entrynode(self, key):
        self.entrynode = self.obj2node[key]    
        return self.entrynode

    def getnodes(self):
        return self.obj2node.itervalues()
        
    # __________________________________________________________
    # Representing variables and constants in Javascript source code 

    def repr_arg(self, arg):
        if isinstance(arg, Constant):
            if isinstance(arg.concretetype, lltype.Primitive):
                return self.primitive_to_str(arg.concretetype, arg.value)
            else:
                assert isinstance(arg.value, lltype._ptr)
                node = self.obj2node.get(arg.value._obj)
                if node is None:
                    return 'null'
                else:
                    return node.ref #get_ref()
        else:
            assert isinstance(arg, Variable)
            return str(arg)

    def repr_type(self, arg):
        try:
            node = self.obj2node.get(arg.value._obj)
            if isinstance(node, ArrayNode):
                return 'Array'
        except:
            pass
        return 'Object'

    def repr_concretetype(self, ct): #used by casts
        try:
            return self.obj2node[ct].ref 
        except KeyError: 
            if isinstance(ct, lltype.Primitive):
                return self.primitives[ct]
            elif isinstance(ct, lltype.Ptr):
                return '' #self.repr_concretetype(type_.TO)
            else: 
                raise TypeError("cannot represent %r" % ct)

    def repr_arg_multi(self, args):
        return [self.repr_arg(arg) for arg in args]

    def repr_constant(self, value):
        " returns node and repr as tuple "
        type_ = lltype.typeOf(value)
        if isinstance(type_, lltype.Primitive):
            repr = self.primitive_to_str(type_, value)
            return None, repr

        elif isinstance(type_, lltype.Ptr):
            value = value._obj

            # special case, null pointer
            if value is None:
                return None, "null"

            node = self.obj2node[value]
            return node, node.ref #node.get_ref()

        elif isinstance(type_, lltype.Array) or isinstance(type_, lltype.Struct):
            node = self.obj2node[value]
            return node, node.constantvalue()

        assert False, "%s not supported" % (type(value))

    def repr_tmpvar(self): 
        count = self._tmpcount 
        self._tmpcount += 1
        return "tmp_" + str(count) 

    def repr_constructor(self, type_):
        return self.obj2node[type_].constructor_ref

    def repr_name(self, obj):
        return self.obj2node[obj].ref

    # __________________________________________________________
    # Primitive stuff

    def float_to_str(self, value):
        repr = "%f" % value
        # llvm requires a . when using e notation
        if "e" in repr and "." not in repr:
            repr = repr.replace("e", ".0e")
        elif repr in ["inf", "nan"] or 'INF' in repr or 'IND' in repr:
            # Need hex repr
            import struct
            packed = struct.pack("d", value)
            if sys.byteorder == 'little':
                packed = packed[::-1]
            
            repr = "0x" + "".join([("%02x" % ord(ii)) for ii in packed])
        return repr

    def char_to_str(self, value):
        x = ord(value)
        if x >= 128:
            r = "cast (ubyte %s to sbyte)" % x
        else:
            r = str(x)
        return r
    
    def primitive_to_str(self, type_, value):
        if type_ is lltype.Bool:
            repr = str(value).lower() #False --> false
        elif type_ is lltype.Char:
            repr = self.char_to_str(value)
        elif type_ is lltype.UniChar:
            repr = str(ord(value))
        elif type_ is lltype.Float:
            repr = self.float_to_str(value)
        else:
            repr = str(value)
        return repr

    # __________________________________________________________
    # Other helpers

    def is_function_ptr(self, arg):
        if isinstance(arg, (Constant, Variable)): 
            arg = arg.concretetype 
            if isinstance(arg, lltype.Ptr):
                if isinstance(arg.TO, lltype.FuncType):
                    return True
        return False
     
    def get_childref(self, parent, child):
        node = self.obj2node[parent]
        return node.get_childref(child)
