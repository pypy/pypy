
import sys

from pypy.translator.llvm.log import log 
from pypy.translator.llvm.funcnode import FuncNode, FuncTypeNode
from pypy.translator.llvm.extfuncnode import ExternalFuncNode
from pypy.translator.llvm.structnode import StructNode, StructVarsizeNode, \
     StructTypeNode, StructVarsizeTypeNode, getindexhelper, \
     FixedSizeArrayTypeNode, FixedSizeArrayNode
from pypy.translator.llvm.arraynode import ArrayNode, StrArrayNode, \
     VoidArrayNode, ArrayTypeNode, VoidArrayTypeNode
from pypy.translator.llvm.opaquenode import OpaqueNode, ExtOpaqueNode, \
     OpaqueTypeNode, ExtOpaqueTypeNode
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.objspace.flow.model import Constant, Variable
from pypy.rpython.memory.lladdress import NULL
from pypy.rpython.objectmodel import Symbolic, ComputedIntSymbolic

log = log.database 

class Database(object): 
    def __init__(self, genllvm, translator): 
        self.genllvm = genllvm
        self.translator = translator
        self.obj2node = {}
        self._pendingsetup = []
        self._tmpcount = 1
        self.helper2ptr = {}
        self.externalfuncs = {}

        self.primitives = Primitives(self)
    
    #_______debuggging______________________________________

    def dump_pbcs(self):
        r = ""
        for k, v in self.obj2node.iteritems():
            
            if isinstance(k, lltype.LowLevelType):
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
    
    #_______setting up and preperation______________________________

    def create_constant_node(self, type_, value):
        node = None
        if isinstance(type_, lltype.FuncType):
            if getattr(value._callable, "suggested_primitive", False):
                node = ExternalFuncNode(self, value)
                self.externalfuncs[node.callable] = value
            else:
                node = FuncNode(self, value)

        elif isinstance(type_, lltype.FixedSizeArray):
            node = FixedSizeArrayNode(self, value)

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
            if hasattr(type_, '_exttypeinfo'):
                node = ExtOpaqueNode(self, value)
            else:
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
        
    def prepare_type(self, type_):
        if type_ in self.obj2node:
            return
        if isinstance(type_, lltype.Primitive):
            pass
        elif isinstance(type_, lltype.Ptr): 
            self.prepare_type(type_.TO)

        elif isinstance(type_, lltype.FixedSizeArray):
            self.addpending(type_, FixedSizeArrayTypeNode(self, type_))
            
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
            if hasattr(type_, '_exttypeinfo'):
                self.addpending(type_, ExtOpaqueTypeNode(self, type_))            
            else:
                self.addpending(type_, OpaqueTypeNode(self, type_))

        else:
            assert False, "need to prepare typerepr %s %s" % (type_, type(type_))

    def prepare_type_multi(self, types):
        for type_ in types:
            self.prepare_type(type_)

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

        # always add type (it is safe)
        self.prepare_type(type_)
        
    def prepare_arg_value(self, const_or_var):
        """if const_or_var is not already in a dictionary self.obj2node,
        the appropriate node gets constructed and gets added to
        self._pendingsetup and to self.obj2node"""
        if isinstance(const_or_var, Constant):
            ct = const_or_var.concretetype
            if isinstance(ct, lltype.Primitive):
                # special cases for address
                if ct is llmemory.Address:
                    fakedaddress = const_or_var.value
                    if fakedaddress is not None and fakedaddress.ob is not None:
                        ptrvalue = fakedaddress.ob
                        ct = lltype.typeOf(ptrvalue)
                    else:
                        return                        
                elif ct is llmemory.WeakGcAddress:
                    return # XXX sometime soon
                else:
                    return
            else:
                assert isinstance(ct, lltype.Ptr), "Preparation of non primitive and non pointer" 
                ptrvalue = const_or_var.value
                
            value = ptrvalue._obj

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
        #log.prepare(const_or_var)
        self.prepare_type(const_or_var.concretetype)
        self.prepare_arg_value(const_or_var)


    def setup_all(self):
        while self._pendingsetup: 
            node = self._pendingsetup.pop(0)
            #log.settingup(node)
            node.setup()

    def set_entrynode(self, key):
        self.entrynode = self.obj2node[key]    
        return self.entrynode

    def getnodes(self):
        return self.obj2node.itervalues()
        
    # __________________________________________________________
    # Representing variables and constants in LLVM source code 

    def repr_arg(self, arg):
        if isinstance(arg, Constant):
            if isinstance(arg.concretetype, lltype.Primitive):
                return self.primitives.repr(arg.concretetype, arg.value)
            else:
                assert isinstance(arg.value, lltype._ptr)
                node = self.obj2node.get(arg.value._obj)
                if node is None:
                    return 'null'
                else:
                    return node.get_ref()
        else:
            assert isinstance(arg, Variable)
            return "%" + str(arg)

    def repr_arg_type(self, arg):
        assert isinstance(arg, (Constant, Variable))
        ct = arg.concretetype 
        return self.repr_type(ct)
    
    def repr_type(self, type_):
        try:
            return self.obj2node[type_].ref 
        except KeyError: 
            if isinstance(type_, lltype.Primitive):
                return self.primitives[type_]
            elif isinstance(type_, lltype.Ptr):
                return self.repr_type(type_.TO) + '*'
            else: 
                raise TypeError("cannot represent %r" %(type_,))
            
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
            repr = self.primitives.repr(type_, value)
            return None, "%s %s" % (self.repr_type(type_), repr)

        elif isinstance(type_, lltype.Ptr):
            toptr = self.repr_type(type_)
            value = value._obj

            # special case, null pointer
            if value is None:
                return None, "%s null" % toptr

            node = self.obj2node[value]
            ref = node.get_pbcref(toptr)
            return node, "%s %s" % (toptr, ref)

        elif isinstance(type_, (lltype.Array, lltype.Struct)):
            node = self.obj2node[value]
            return node, node.constantvalue()

        elif isinstance(type_, lltype.OpaqueType):
            node = self.obj2node[value]
            if isinstance(node, ExtOpaqueNode):
                return node, node.constantvalue()
                
        assert False, "%s not supported" % (type(value))

    def repr_tmpvar(self): 
        count = self._tmpcount 
        self._tmpcount += 1
        return "%tmp_" + str(count) 

    def repr_constructor(self, type_):
        return self.obj2node[type_].constructor_ref

    def repr_name(self, obj):
        " simply returns a reference to constant value "
        return self.obj2node[obj].ref

    def repr_value(self, value):
        # XXX Testing
        return self.obj2node[value].get_ref()

    # __________________________________________________________
    # Other helpers

    def get_machine_word(self):
        return self.primitives[lltype.Signed]

    def get_machine_uword(self):
        return self.primitives[lltype.Unsigned]

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


class Primitives(object):
    def __init__(self, database):        
        self.database = database
        self.types = {
            lltype.Char: "sbyte",
            lltype.Bool: "bool",
            lltype.Float: "double",
            lltype.UniChar: "uint",
            lltype.Void: "void",
            lltype.UnsignedLongLong: "ulong",
            lltype.SignedLongLong: "long",
            llmemory.Address: "sbyte*",
            llmemory.WeakGcAddress: "sbyte*",
            }

        # 32 bit platform
        if sys.maxint == 2**31-1:
            self.types.update({
                lltype.Signed: "int",
                lltype.Unsigned: "uint" })
            
        # 64 bit platform
        elif sys.maxint == 2**63-1:        
            self.types.update({
                lltype.Signed: "long",
                lltype.Unsigned: "ulong" })            
        else:
            raise Exception("Unsupported platform - unknown word size")
            
        self.reprs = {
            lltype.SignedLongLong : self.repr_signed,
            lltype.Signed : self.repr_signed,
            lltype.UnsignedLongLong : self.repr_unsigned,
            lltype.Unsigned : self.repr_unsigned,
            lltype.Float : self.repr_float,
            lltype.Char : self.repr_char,
            lltype.UniChar : self.repr_unichar,
            lltype.Bool : self.repr_bool,
            lltype.Void : self.repr_void,
            llmemory.Address : self.repr_address,
            llmemory.WeakGcAddress : self.repr_weakgcaddress,
            }        
        #XXX
#         try:
#             import ctypes
#         except ImportError:
#             pass
#         else:
#             from pypy.rpython.rctypes import rcarithmetic as rcarith
#             types.update({rcarith.CByte : 'sbyte',
#                           rcarith.CUByte : 'ubyte',
#                           rcarith.CShort : 'short',
#                           rcarith.CUShort : 'ushort',
#                           rcarith.CInt : 'int',
#                           rcarith.CUInt : 'uint',
#                           rcarith.CLong : types[lltype.Signed],
#                           rcarith.CULong : types[lltype.Unsigned],
#                           rcarith.CLonglong : 'long',
#                           rcarith.CULonglong : 'ulong'})
        
    def __getitem__(self, key):
        return self.types[key]
        
    def repr(self, type_, value):
        try:
            return self.reprs[type_](type_, value)
        except KeyError:
            raise Exception, "unsupported primitive type %r, value %r" % (type_, value)
        
    def repr_bool(self, type_, value):
        return str(value).lower() #False --> false

    def repr_void(self, type_, value):
        return 'void'
  
    def repr_char(self, type_, value):
        x = ord(value)
        if x >= 128:
            r = "cast (ubyte %s to sbyte)" % x
        else:
            r = str(x)
        return r

    def repr_unichar(self, type_, value):
        return str(ord(value))

    def repr_float(self, type_, value):
        repr = "%f" % value
        # llvm requires a . when using e notation
        if "e" in repr and "." not in repr:
            repr = repr.replace("e", ".0e")
        elif repr in ["inf", "nan"]:
            # Need hex repr
            import struct
            packed = struct.pack("d", value)
            if sys.byteorder == 'little':
                packed = packed[::-1]
            
            repr = "0x" + "".join([("%02x" % ord(ii)) for ii in packed])
        return repr

    def repr_address(self, type_, value):
        if value is NULL:
            return 'null'

        assert isinstance(value, llmemory.fakeaddress)

        if value.offset is None:
            if value.ob is None:
                return 'null'
            else:
                obj = value.ob._obj
                typename = self.database.repr_type(lltype.typeOf(obj))
                ref = self.database.repr_name(obj)
        else:
            from_, indices, to = self.get_offset(value.offset)
            indices_as_str = ", ".join("%s %s" % (w, i) for w, i in indices)

            original_typename = self.database.repr_type(from_)
            orignal_ref = self.database.repr_name(value.ob._obj)

            typename = self.database.repr_type(to)
            ref = "getelementptr(%s* %s, %s)" % (original_typename,
                                                 orignal_ref,
                                                 indices_as_str)
            
        res = "cast(%s* %s to sbyte*)" % (typename, ref)
        return res    
    
    def repr_weakgcaddress(self, type_, value):
        assert isinstance(value, llmemory.fakeweakaddress)
        log.settingup("XXXX weakgcaddress completely ignored...")
        return 'null'

    def repr_signed(self, type_, value):
        if isinstance(value, Symbolic):
            return self.repr_symbolic(type_, value)
        return str(value)
    
    def repr_unsigned(self, type_, value):
        return str(value)

    def repr_symbolic(self, type_, value):
        """ returns an int value for pointer arithmetic - not sure this is the
        llvm way, but well XXX need to fix adr_xxx operations  """
        if isinstance(value, llmemory.AddressOffset):
            from_, indices, to = self.get_offset(value)
            indices_as_str = ", ".join("%s %s" % (w, i) for w, i in indices)
            r = self.database.repr_type
            repr = "cast(%s* getelementptr(%s* null, %s) to int)" % (r(to),
                                                                     r(from_),
                                                                     indices_as_str)
        elif isinstance(value, ComputedIntSymbolic):
            # XXX what does this do?  Is this safe?
            repr = '%d' % value.compute_fn()
        else:
            raise NotImplementedError("symbolic: %r" % (value,))
        
        return repr
    
    def get_offset(self, value, fromoffset=False):
        " return (from_type, (indices, ...), to_type) "        
        word = self.database.get_machine_word()
        uword = self.database.get_machine_uword()
        indices = []

        if isinstance(value, llmemory.ItemOffset):
            # skips over a fixed size item (eg array access)
            from_ = value.TYPE
            indices.append((word, value.repeat))
            to = value.TYPE
        
        elif isinstance(value, llmemory.FieldOffset):
            # jumps to a field position in a struct
            pos = getindexhelper(value.fldname, value.TYPE)
            from_ = value.TYPE
            if not fromoffset:
                indices.append((word, 0))
            indices.append((uword, pos))
            to = getattr(value.TYPE, value.fldname)            
                
        elif isinstance(value, llmemory.ArrayItemsOffset):
            # jumps to the beginning of array area
            if not fromoffset:
                indices.append((word, 0))
            if not isinstance(value.TYPE, lltype.FixedSizeArray):
                indices.append((uword, 1))
            from_ = value.TYPE
            to = value.TYPE.OF

        elif isinstance(value, llmemory.CompositeOffset):
            from_, indices, to = self.get_offset(value.offsets[0])
            indices = list(indices)
            for item in value.offsets[1:]:
                _, more, to = self.get_offset(item, fromoffset=True)
                indices.extend(more)
        else:
            raise Exception("unsupported offset")

        return from_, indices, to
    
