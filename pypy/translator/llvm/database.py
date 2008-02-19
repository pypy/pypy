import sys

from pypy.translator.llvm.log import log 

from pypy.translator.llvm.typedefnode import create_typedef_node
from pypy.translator.llvm.typedefnode import getindexhelper

from pypy.translator.llvm.funcnode import FuncImplNode
from pypy.translator.llvm.extfuncnode import ExternalFuncNode
from pypy.translator.llvm.opaquenode import OpaqueNode, ExtOpaqueNode
from pypy.translator.llvm.structnode import StructNode, StructVarsizeNode, \
     FixedSizeArrayNode
from pypy.translator.llvm.arraynode import ArrayNode, StrArrayNode, \
     VoidArrayNode, ArrayNoLengthNode, StrArrayNoLengthNode, DebugStrNode
     
from pypy.rpython.lltypesystem import lltype, llmemory, llarena, rffi
from pypy.objspace.flow.model import Constant, Variable
from pypy.rlib.objectmodel import Symbolic, ComputedIntSymbolic
from pypy.rlib.objectmodel import CDefinedIntSymbolic
from pypy.rlib import objectmodel
from pypy.rlib import jit

log = log.database 

def var_size_type(T):
    " returns None if T not varsize "
    if not T._is_varsize():
        return None
    elif isinstance(T, lltype.Array):
        return T.OF
    elif isinstance(T, lltype.Struct):
        return T._arrayfld
    else:
        assert False, "unknown type"
        
class Database(object): 
    def __init__(self, genllvm, translator): 
        self.genllvm = genllvm
        self.translator = translator
        self.gctransformer = None
        self.obj2node = {}
        self._pendingsetup = []
        self._tmpcount = 1

        self.primitives = Primitives(self)

        # keep ordered list for when we write
        self.funcnodes = []
        self.typedefnodes = []
        self.containernodes = []

        self.debugstringnodes = []


    #_______debuggging______________________________________

    def dump_pbcs(self):
        r = ""
        for k, v in self.obj2node.iteritems():

            if isinstance(v, FuncImplNode):
                continue
            
            if isinstance(k, lltype.LowLevelType):
                continue

            assert isinstance(lltype.typeOf(k), lltype.ContainerType)
            
            # Only dump top levels
            p, _ = lltype.parentlink(k)
            type_ = self.repr_type(lltype.Ptr(lltype.typeOf(k)))
            r += "\ndump_pbcs %s (%s)\n" \
                 "parent %s\n" \
                 "type %s\n" \
                 "ref -> %s \n" % (v, k, p, type_, v.ref)
        return r
    
    #_______setting up and preparation______________________________

    def create_constant_node(self, type_, value):
        node = None
        if isinstance(type_, lltype.FuncType):
            if getattr(value, 'external', None) == 'C':
                node = ExternalFuncNode(self, value)
            else:
                node = FuncImplNode(self, value)

        elif isinstance(type_, lltype.FixedSizeArray):
            node = FixedSizeArrayNode(self, value)

        elif isinstance(type_, lltype.Struct):
            if type_._arrayfld:
                node = StructVarsizeNode(self, value)
            else:
                node = StructNode(self, value)
                    
        elif isinstance(type_, lltype.Array):
            if type_.OF is lltype.Char:
                if type_._hints.get("nolength", False):
                    node = StrArrayNoLengthNode(self, value)
                else:
                    node = StrArrayNode(self, value)
            elif type_.OF is lltype.Void:
                node = VoidArrayNode(self, value)
            else:
                if type_._hints.get("nolength", False):
                    node = ArrayNoLengthNode(self, value)
                else:
                    node = ArrayNode(self, value)

        elif isinstance(type_, lltype.OpaqueType):
            if type_.hints.get('render_structure', False):
                node = ExtOpaqueNode(self, value)
            else:
                node = OpaqueNode(self, value)

        elif type_ is llmemory.WeakRef:
            # XXX this uses a hack in translator.c.node.weakrefnode_factory()
            # because we need to obtain not just *a* conversion of the weakref
            # by the gcpolicy, but *the same* one as was already registered
            # in the genc database and seen by the gctransformer
            value = value._converted_weakref
            return self.create_constant_node(lltype.typeOf(value), value)

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
            return

        if isinstance(type_, lltype.Ptr):
            self.prepare_type(type_.TO)
        else:
            node = create_typedef_node(self, type_)
            self.addpending(type_, node)
            self.typedefnodes.append(node)

    def prepare_type_multi(self, types):
        for type_ in types:
            self.prepare_type(type_)

    def prepare_constant(self, ct, value):
        # always add type (it is safe)
        self.prepare_type(ct)

        if isinstance(ct, lltype.Primitive):
            # special cases for address
            if ct is llmemory.Address:
                # prepare the constant data which this address references
                fakedaddress = value
                if fakedaddress:
                    ptrvalue = fakedaddress.ptr
                    ct = lltype.typeOf(ptrvalue)
                    self.prepare_constant(ct, ptrvalue)

            else:
                if isinstance(value, llmemory.AddressOffset):
                    self.prepare_offset(value)
            return

        if isinstance(ct, lltype.Ptr):
            ptrvalue = value
            ct = ct.TO
            value = ptrvalue._obj
            # we dont need a node for nulls
            if value is None:
                return
            # we dont need a node for tagged pointers
            if isinstance(value, int):
                return

        # we can share data via pointers
        assert isinstance(ct, lltype.ContainerType)
        if value not in self.obj2node: 
            self.addpending(value, self.create_constant_node(ct, value))
        
    def prepare_arg(self, const_or_var):
        """if const_or_var is not already in a dictionary self.obj2node,
        the appropriate node gets constructed and gets added to
        self._pendingsetup and to self.obj2node"""
        if isinstance(const_or_var, Constant):
            self.prepare_constant(const_or_var.concretetype,
                                  const_or_var.value)
        else:
            assert isinstance(const_or_var, Variable)
            self.prepare_type(const_or_var.concretetype)


    def prepare_offset(self, offset):
        if isinstance(offset, llmemory.CompositeOffset):
            for value in offset.offsets:
                self.prepare_offset(value)
        elif isinstance(offset, llarena.RoundedUpForAllocation):
            self.prepare_offset(offset.basesize)
        elif hasattr(offset, 'TYPE'):
            self.prepare_type(offset.TYPE)

    def setup_all(self):
        self.gcpolicy.setup()
        while self._pendingsetup: 
            node = self._pendingsetup.pop()
            #log.settingup(node)
            node.setup()

    def set_entrynode(self, key):
        self.entrynode = self.obj2node[key]    
        return self.entrynode

    def getnodes(self):
        return self.obj2node.itervalues()

    def gettypedefnodes(self):
        return self.typedefnodes
        
    # __________________________________________________________
    # Representing variables and constants in LLVM source code 

    def to_getelementptr(self, value):
        # so we build the thing up instead
        p = value
        children = []
        while True:
            p, c = lltype.parentlink(p)
            if p is None:
                break
            children.append((p, c))

        children.reverse()
        
        TYPE = lltype.typeOf(children[0][0])
        parentnode = self.obj2node[children[0][0]]

        indices = [("i32", 0)]

        for _, ii in children:
            typedefnode = self.obj2node[TYPE]
            if isinstance(ii, str):
                TYPE = typedefnode.fieldname_to_getelementptr(indices, ii)
            else:
                TYPE = typedefnode.indexref_to_getelementptr(indices, ii)

        indices_str = ', '.join ([('%s %s' % (x,y)) for x, y in indices])
        ref = "getelementptr(%s* %s, %s)" % (
            parentnode.get_typerepr(),
            parentnode.ref,
            indices_str)

        return ref

    def get_ref(self, value):
        node = self.obj2node[value]
        T = lltype.typeOf(value)
        p, c = lltype.parentlink(value)
        if p is None:
            ref = node.ref
            VT = var_size_type(T)
            if VT and VT is not lltype.Void:
                ref = "bitcast(%s* %s to %s*)" % (node.get_typerepr(),
                                                  ref,
                                                  self.repr_type(T))
        else:
            ref = self.to_getelementptr(value)
            
            if isinstance(node, FixedSizeArrayNode):
                assert isinstance(value, lltype._subarray)

                # XXX UGLY (but needs fixing outside of genllvm)
                #  ptr -> array of len 1 (for now, since operations expect this)
                ref = "bitcast(%s* %s to %s*)" % (self.repr_type(T.OF),
                                                  ref,
                                                  self.repr_type(T))

        return ref

    def repr_arg(self, arg):
        if isinstance(arg, Constant):
            if isinstance(arg.concretetype, lltype.Primitive):
                return self.primitives.repr(arg.concretetype, arg.value)
            else:
                assert isinstance(arg.value, lltype._ptr)
                if not arg.value:
                    return 'null'
                else:
                    return self.get_ref(arg.value._obj)
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
            ref = self.get_ref(value)
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

    # __________________________________________________________
    # Other helpers

    def get_machine_word(self):
        return self.primitives[lltype.Signed]

    def is_function_ptr(self, arg):
        if isinstance(arg, (Constant, Variable)): 
            arg = arg.concretetype 
            if isinstance(arg, lltype.Ptr):
                if isinstance(arg.TO, lltype.FuncType):
                    return True
        return False

    def create_debug_string(self, s):
        r = DebugStrNode(s)
        self.debugstringnodes.append(r)
        return r

class Primitives(object):
    def __init__(self, database):        
        self.database = database
        self.types = {
            lltype.Char: "i8",
            lltype.Bool: "i1",
            lltype.SingleFloat: "float",
            lltype.Float: "double",
            lltype.UniChar: "i32",
            lltype.Void: "void",
            lltype.UnsignedLongLong: "i64",
            lltype.SignedLongLong: "i64",
            llmemory.Address: "i8*",
            }

        # 32 bit platform
        if sys.maxint == 2**31-1:
            self.types.update({
                lltype.Signed: "i32",
                lltype.Unsigned: "i32" })
            
        # 64 bit platform
        elif sys.maxint == 2**63-1:        
            self.types.update({
                lltype.Signed: "i64",
                lltype.Unsigned: "i64" })            
        else:
            raise Exception("Unsupported platform - unknown word size")

        self.reprs = {
            lltype.SignedLongLong : self.repr_signed,
            lltype.Signed : self.repr_signed,
            lltype.UnsignedLongLong : self.repr_default,
            lltype.Unsigned : self.repr_default,
            lltype.SingleFloat: self.repr_singlefloat,
            lltype.Float : self.repr_float,
            lltype.Char : self.repr_char,
            lltype.UniChar : self.repr_unichar,
            lltype.Bool : self.repr_bool,
            lltype.Void : self.repr_void,
            llmemory.Address : self.repr_address,
            }        

        try:
            import ctypes
        except ImportError:
            pass
        else:
            def update(from_, type):
                if from_ not in self.types:
                    self.types[from_] = type
                if from_ not in self.reprs:
                    self.reprs[from_] = self.repr_default

            for tp in [rffi.SIGNEDCHAR, rffi.UCHAR, rffi.SHORT,
                       rffi.USHORT, rffi.INT, rffi.UINT, rffi.LONG, rffi.ULONG,
                       rffi.LONGLONG, rffi.ULONGLONG]:
                bits = rffi.size_and_sign(tp)[0] * 8
                update(tp, 'i%s' % bits)

    def get_attrs_for_type(self, type):
        # because we want to bind to external functions that depend
        # on sign/zero extensions, we need to use these attributes in function sigs
        # note that this is not needed for internal functions because they use
        # casts if necessary
        type_attrs = ""
        if not isinstance(type, lltype.Number):
            return type_attrs
        size, sign = rffi.size_and_sign(type)
        if size < 4:
            if not sign:
                type_attrs += "signext"
            else:
                type_attrs += "zeroext"
        return type_attrs
 
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
            # XXX check this really works
            r = "trunc (i16 %s to i8)" % x
        else:
            r = str(x)
        return r

    def repr_unichar(self, type_, value):
        return str(ord(value))

    def repr_float(self, type_, value):
        from pypy.rlib.rarithmetic import isinf, isnan

        if isinf(value) or isnan(value):
            # Need hex repr
            import struct
            packed = struct.pack("d", value)
            if sys.byteorder == 'little':
                packed = packed[::-1]
            
            repr = "0x" + "".join([("%02x" % ord(ii)) for ii in packed])
        else:
            repr = "%f" % value
            
            # llvm requires a . when using e notation
            if "e" in repr and "." not in repr:
                repr = repr.replace("e", ".0e")

        return repr

    def repr_singlefloat(self, type_, value):
        from pypy.rlib.rarithmetic import isinf, isnan
        
        f = float(value)
        if isinf(f) or isnan(f):
            import struct
            packed = value._bytes
            if sys.byteorder == 'little':
                packed = packed[::-1]
            assert len(packed) == 4
            repr =  "0x" + "".join([("%02x" % ord(ii)) for ii in packed])
        else:
            #repr = "%f" % f
            # XXX work around llvm2.1 bug, seems it doesnt like constants for floats
            repr = "fptrunc(double %f to float)" % f
            
            # llvm requires a . when using e notation
            if "e" in repr and "." not in repr:
                repr = repr.replace("e", ".0e")
        return repr

    def repr_address(self, type_, value):
        # XXX why-o-why isnt this an int ???
        if not value:
            return 'null'
        ptr = value.ptr
        node, ref = self.database.repr_constant(ptr)
        res = "bitcast(%s to i8*)" % (ref,)
        return res

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
            elif value is objectmodel.running_on_llinterp:
                repr = '0'
            else:
                raise NotImplementedError("CDefinedIntSymbolic: %r" % (value,))
        else:
            raise NotImplementedError("symbolic: %r" % (value,))
        
        return repr
    
    def repr_offset(self, value):
        if isinstance(value, llarena.RoundedUpForAllocation):
            # XXX not supported when used in a CompositeOffset
            from pypy.rpython.tool import rffi_platform
            align = rffi_platform.memory_alignment()
            r_basesize = self.repr_offset(value.basesize)
            # Note that the following expression is known to crash 'llc';
            # you may need to upgrade llvm.
            return "and(i32 add(i32 %s, i32 %d), i32 %d)" % (
                r_basesize, align-1, ~(align-1))

        from_, indices, to = self.get_offset(value, [])

        if from_ is lltype.Void or not indices:
            return "0"
        assert to is not lltype.Void

        r = self.database.repr_type
        indices_as_str = ", ".join("%s %s" % (w, i) for w, i in indices)
        return "ptrtoint(%s* getelementptr(%s* null, %s) to i32)" % (r(to),
                                                                     r(from_),
                                                                     indices_as_str)

    def get_offset(self, value, indices):
        " return (from_type, (indices, ...), to_type) "

        word = self.database.get_machine_word()

        if isinstance(value, llmemory.ItemOffset):
            if not indices:
                indices.append((word, 0))
            
            # skips over a fixed size item (eg array access)
            from_ = value.TYPE
            if from_ is not lltype.Void:
                lasttype, lastvalue = indices[-1]
                assert lasttype == word
                indices[-1] = (word, lastvalue + value.repeat)
            to = value.TYPE
        
        elif isinstance(value, llmemory.FieldOffset):
            if not indices:
                indices.append((word, 0))

            # jumps to a field position in a struct
            from_ = value.TYPE
            pos = getindexhelper(self.database, value.fldname, value.TYPE)
            indices.append((word, pos))
            to = getattr(value.TYPE, value.fldname)            

        elif isinstance(value, llmemory.ArrayLengthOffset):
            assert not value.TYPE._hints.get("nolength", False)

            if not indices:
                indices.append((word, 0))

            # jumps to the place where the array length is stored
            from_ = value.TYPE     # <Array of T> or <GcArray of T>
            assert isinstance(value.TYPE, lltype.Array)
            typedefnode = self.database.obj2node[value.TYPE]
            indexref = typedefnode.indexref_for_length()
            indices.append((word, indexref))
            to = lltype.Signed

        elif isinstance(value, llmemory.ArrayItemsOffset):
            if not indices:
                if isinstance(value.TYPE, lltype.Array) and value.TYPE._hints.get("nolength", False):
                    pass
                else:
                    indices.append((word, 0))

            if value.TYPE.OF is lltype.Void:
                # skip over the whole structure in order to get to the
                # (not-really-existent) array part
                return self.get_offset(llmemory.ItemOffset(value.TYPE),
                                       indices)

            # jumps to the beginning of array area
            from_ = value.TYPE
            if not isinstance(value.TYPE, lltype.FixedSizeArray) and not value.TYPE._hints.get("nolength", False):
                typedefnode = self.database.obj2node[value.TYPE]
                indexref = typedefnode.indexref_for_items()
                indices.append((word, indexref))
                indices.append((word, 0)) # go to the 1st item
            if isinstance(value.TYPE, lltype.FixedSizeArray):
                indices.append((word, 0)) # go to the 1st item
                            
            to = value.TYPE.OF

        elif isinstance(value, llmemory.CompositeOffset):
            from_, indices, to = self.get_offset(value.offsets[0], indices)
            for item in value.offsets[1:]:
                _, indices, to1 = self.get_offset(item, indices)
                if to1 is not lltype.Void:
                    to = to1

        else:
            raise Exception("unsupported offset")

        return from_, indices, to    
