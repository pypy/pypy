
import sys

from pypy.translator.llvm.log import log 
from pypy.translator.llvm.funcnode import FuncNode, FuncTypeNode
from pypy.translator.llvm.extfuncnode import ExternalFuncNode, SimplerExternalFuncNode
from pypy.translator.llvm.structnode import StructNode, StructVarsizeNode, \
     StructTypeNode, StructVarsizeTypeNode, getindexhelper, \
     FixedSizeArrayTypeNode, FixedSizeArrayNode
from pypy.translator.llvm.arraynode import ArrayNode, StrArrayNode, \
     VoidArrayNode, ArrayTypeNode, VoidArrayTypeNode
from pypy.translator.llvm.opaquenode import OpaqueNode, ExtOpaqueNode, \
     OpaqueTypeNode, ExtOpaqueTypeNode
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.objspace.flow.model import Constant, Variable
from pypy.rlib.objectmodel import Symbolic, ComputedIntSymbolic
from pypy.rlib.objectmodel import CDefinedIntSymbolic
from pypy.rlib import objectmodel
from pypy.rlib import jit

log = log.database 

class Database(object): 
    def __init__(self, genllvm, translator): 
        self.genllvm = genllvm
        self.translator = translator
        self.obj2node = {}
        self._pendingsetup = []
        self._tmpcount = 1
        self.helper2ptr = {}

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
            elif hasattr(value, '_external_name'):
                node = ExternalFuncNode(self, value, value._external_name)

            elif getattr(value, 'external', None) == 'C':
                node = SimplerExternalFuncNode(self, value)
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
            if type_ is llmemory.Address:
                # prepare the constant data which this address references
                assert isinstance(value, llmemory.fakeaddress)
                if value:
                    self.prepare_constant(lltype.typeOf(value.ptr), value.ptr)
            return

        if isinstance(type_, lltype.Ptr) and isinstance(value._obj, int):
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
                    if fakedaddress:
                        ptrvalue = fakedaddress.ptr
                        ct = lltype.typeOf(ptrvalue)
                    else:
                        return                        
##                elif ct is llmemory.WeakGcAddress:
##                    return # XXX sometime soon

                else:
                    if isinstance(const_or_var.value, llmemory.AddressOffset):
                        self.prepare_offset(const_or_var.value)
                    return
            else:
                assert isinstance(ct, lltype.Ptr), "Preparation of non primitive and non pointer" 
                ptrvalue = const_or_var.value
                
            value = ptrvalue._obj

            if isinstance(value, int):
                return

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

    def prepare_offset(self, offset):
        if isinstance(offset, llmemory.CompositeOffset):
            for value in offset.offsets:
                self.prepare_offset(value)
        else:
            self.prepare_type(offset.TYPE)

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
                if isinstance(arg.value._obj, int):
                    rt = self.repr_type(arg.concretetype)
                    v = repr(arg.value._obj)
                    return 'cast (int %s to %s)'%(v, rt)
                elif not arg.value:
                    return 'null'
                else:
                    node = self.obj2node[arg.value._obj]
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

            if isinstance(value, int):
                return None, '%s cast (int %s to %s)'%(toptr, value, toptr)

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
            #llmemory.WeakGcAddress: "sbyte*",
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
            lltype.UnsignedLongLong : self.repr_default,
            lltype.Unsigned : self.repr_default,
            lltype.Float : self.repr_float,
            lltype.Char : self.repr_char,
            lltype.UniChar : self.repr_unichar,
            lltype.Bool : self.repr_bool,
            lltype.Void : self.repr_void,
            llmemory.Address : self.repr_address,
            #llmemory.WeakGcAddress : self.repr_weakgcaddress,
            }        

        try:
            import ctypes
        except ImportError:
            pass
        else:
            from pypy.rpython.rctypes import rcarithmetic as rcarith

            def update(from_, type):
                if from_ not in self.types:
                    self.types[from_] = type
                if from_ not in self.reprs:
                    self.reprs[from_] = self.repr_default
            
            for k, v in [
                (rcarith.CByte, self.types[lltype.Char]),
                (rcarith.CUByte, 'ubyte'),
                (rcarith.CShort, 'short'),
                (rcarith.CUShort, 'ushort'),
                (rcarith.CInt, 'int'),
                (rcarith.CUInt, 'uint'),
                (rcarith.CLong, self.types[lltype.Signed]),
                (rcarith.CULong, self.types[lltype.Unsigned]),
                (rcarith.CLonglong, self.types[lltype.SignedLongLong]),
                (rcarith.CULonglong, self.types[lltype.UnsignedLongLong])]:
                update(k, v)
        
    def __getitem__(self, key):
        return self.types[key]
        
    def repr(self, type_, value):
        try:
            reprfn = self.reprs[type_]
        except KeyError:
            raise Exception, "unsupported primitive type %r, value %r" % (type_, value)
        else:
            return reprfn(type_, value)
        
    def repr_default(self, type_, value):
        return str(value)

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
        if not value:
            return 'null'
        ptr = value.ptr
        node, ref = self.database.repr_constant(ptr)
        res = "cast(%s to sbyte*)" % (ref,)
        return res

    def repr_weakgcaddress(self, type_, value):
        assert isinstance(value, llmemory.fakeweakaddress)
        log.WARNING("XXX weakgcaddress completely ignored...")
        return 'null'

    def repr_signed(self, type_, value):
        if isinstance(value, Symbolic):
            return self.repr_symbolic(type_, value)
        return str(value)
    
    def repr_symbolic(self, type_, value):
        """ returns an int value for pointer arithmetic - not sure this is the
        llvm way, but well XXX need to fix adr_xxx operations  """
        if (type(value) == llmemory.GCHeaderOffset or
            type(value) == llmemory.AddressOffset):
            repr = 0
        
        elif isinstance(value, llmemory.AddressOffset):
            repr = self.repr_offset(value)

        elif isinstance(value, ComputedIntSymbolic):
            # force the ComputedIntSymbolic to become a real integer value now
            repr = '%d' % value.compute_fn()

        elif isinstance(value, CDefinedIntSymbolic):
            if value is objectmodel.malloc_zero_filled:
                repr = '1'
            elif value is jit._we_are_jitted:
                repr = '0'
            else:
                raise NotImplementedError("CDefinedIntSymbolic: %r" % (value,))
        else:
            raise NotImplementedError("symbolic: %r" % (value,))
        
        return repr
    
    def repr_offset(self, value):
        from_, indices, to = self.get_offset(value)

        # void array special cases
        if isinstance(from_, lltype.Array) and from_.OF is lltype.Void:
            assert not isinstance(value, (llmemory.FieldOffset, llmemory.ItemOffset))
            if isinstance(value, llmemory.ArrayLengthOffset):
                pass # ok cases!
            elif isinstance(value, llmemory.ArrayItemsOffset):
                to = from_
                indices = [(self.database.get_machine_word(), 1)]
            else:
                s = value.offsets[0]
                isinstance(value, llmemory.CompositeOffset) 
                return self.repr_offset(s)

        if from_ is lltype.Void:
            assert isinstance(value, llmemory.ItemOffset)
            return "0"

        r = self.database.repr_type
        indices_as_str = ", ".join("%s %s" % (w, i) for w, i in indices)
        return "cast(%s* getelementptr(%s* null, %s) to int)" % (r(to),
                                                                 r(from_),
                                                                 indices_as_str)

    def get_offset(self, value, initialindices=None):
        " return (from_type, (indices, ...), to_type) "
        word = self.database.get_machine_word()
        uword = self.database.get_machine_uword()
        indices = initialindices or [(word, 0)]

        if isinstance(value, llmemory.ItemOffset):
            # skips over a fixed size item (eg array access)
            from_ = value.TYPE
            lasttype, lastvalue = indices[-1]
            assert lasttype == word
            indices[-1] = (word, lastvalue + value.repeat)
            to = value.TYPE
        
        elif isinstance(value, llmemory.FieldOffset):
            # jumps to a field position in a struct
            from_ = value.TYPE
            pos = getindexhelper(value.fldname, value.TYPE)
            indices.append((uword, pos))
            to = getattr(value.TYPE, value.fldname)            

        elif isinstance(value, llmemory.ArrayLengthOffset):
            # jumps to the place where the array length is stored
            from_ = value.TYPE     # <Array of T> or <GcArray of T>
            assert isinstance(value.TYPE, lltype.Array)
            indices.append((uword, 0))
            to = lltype.Signed

        elif isinstance(value, llmemory.ArrayItemsOffset):
            # jumps to the beginning of array area
            from_ = value.TYPE
            if not isinstance(value.TYPE, lltype.FixedSizeArray):
                indices.append((uword, 1))
            indices.append((word, 0))    # go to the 1st item
            to = value.TYPE.OF

        elif isinstance(value, llmemory.CompositeOffset):
            from_, indices, to = self.get_offset(value.offsets[0], indices)
            for item in value.offsets[1:]:
                _, indices, to = self.get_offset(item, indices)

        else:
            raise Exception("unsupported offset")

        return from_, indices, to    
