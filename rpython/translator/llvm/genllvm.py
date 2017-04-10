from itertools import count
from os import devnull, write, environ
import py
import re

from py.path import local
from py.process import cmdexec

from rpython.translator import cdir
from rpython.flowspace.model import mkentrymap, Constant, Variable
from rpython.memory.gctransform.llvmgcroot import (
     LLVMGcRootFrameworkGCTransformer)
from rpython.memory.gctransform.refcounting import RefcountingGCTransformer
from rpython.memory.gctransform.shadowstack import (
     ShadowStackFrameworkGCTransformer)
from rpython.memory.gctypelayout import WEAKREF, convert_weakref_to
from rpython.rlib import exports
from rpython.rlib.compilerinfo import COMPILER_INFO
from rpython.rlib.jit import _we_are_jitted
from rpython.rlib.objectmodel import (Symbolic, ComputedIntSymbolic,
     CDefinedIntSymbolic, malloc_zero_filled)
from rpython.rtyper.annlowlevel import MixLevelHelperAnnotator
from rpython.rtyper.llannotation import lltype_to_annotation
from rpython.rtyper.lltypesystem import (llarena, llgroup, llmemory, lltype,
     rffi)
from rpython.rtyper.lltypesystem.ll2ctypes import (_llvm_needs_header,
     _array_mixin)
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.lltypesystem.lltype import getfunctionptr
from rpython.rtyper.tool.rffi_platform import memory_alignment
from rpython.translator.backendopt.removenoops import remove_same_as
from rpython.translator.backendopt.ssa import SSI_to_SSA
from rpython.translator.gensupp import uniquemodulename
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.translator.unsimplify import (remove_double_links,
     no_links_to_startblock)
from rpython.tool.udir import udir


database = None
align = memory_alignment()


class Type(object):
    varsize = False
    needs_gc_header = False

    def setup_from_lltype(self, db, type):
        pass

    def repr_type(self, extra_len=None):
        return self.typestr

    def repr_of_type(self):
        return self.typestr

    def is_zero(self, value):
        raise NotImplementedError("Override in subclass.")

    def get_extra_len(self, value):
        raise NotImplementedError("Override in subclass.")

    def repr_value(self, value):
        raise NotImplementedError("Override in subclass.")

    def repr_type_and_value(self, value):
        if self.varsize:
            self.repr_type(None)
            extra_len = self.get_extra_len(value)
            return '{} {}'.format(self.repr_type(extra_len),
                                  self.repr_value(value, extra_len))
        return '{} {}'.format(self.repr_type(), self.repr_value(value))

    def repr_ref(self, ptr_type, obj):
        global_attrs = ''
        if obj in exports.EXPORTS_obj2name:
            tmp = exports.EXPORTS_obj2name[obj]
            for key, value in exports.EXPORTS_obj2name.iteritems():
                if value == tmp:
                    export_obj = key
            if export_obj is obj:
                name = '@' + tmp
            else:
                orig_ptr_type = lltype.Ptr(lltype.typeOf(export_obj))
                orig_ptr = lltype._ptr(orig_ptr_type, export_obj)
                orig_ptr_type_llvm = database.get_type(orig_ptr_type)
                ptr_type.refs[obj] = 'bitcast({} to {})'.format(
                        orig_ptr_type_llvm.repr_type_and_value(orig_ptr),
                        ptr_type.repr_type())
                return
        else:
            global_attrs += 'internal '
            name = database.unique_name('@global')
        if (hasattr(obj._TYPE, '_hints') and
            obj._TYPE._hints.get('immutable', False) and
            obj._TYPE._gckind != 'gc'):
            global_attrs += 'constant'
        else:
            global_attrs += 'global'

        if self.varsize:
            extra_len = self.get_extra_len(obj)
            ptr_type.refs[obj] = 'bitcast({} {} to {})'.format(
                    ptr_type.repr_type(extra_len), name,
                    ptr_type.repr_type(None))
        else:
            ptr_type.refs[obj] = name
        database.f.write('{} = {} {}\n'.format(
                name, global_attrs, self.repr_type_and_value(obj)))


class VoidType(Type):
    typestr = 'void'

    def is_zero(self, value):
        return True

    def repr_value(self, value, extra_len=None):
        if value is None:
            return 'null'
        raise TypeError


class IntegralType(Type):
    def __init__(self, bitwidth, unsigned):
        self.bitwidth = bitwidth
        self.unsigned = unsigned
        self.typestr = 'i{}'.format(self.bitwidth)

    def is_zero(self, value):
        if isinstance(value, (int, long)):
            return value == 0
        if isinstance(value, str):
            return value == '\00'
        if isinstance(value, unicode):
            return value == u'\00'
        if isinstance(value, Symbolic):
            return False
        if value is None:
            return True
        raise NotImplementedError

    def repr_value(self, value, extra_len=None):
        if isinstance(value, (int, long)):
            return str(value)
        elif isinstance(value, (str, unicode)):
            return str(ord(value))
        elif isinstance(value, ComputedIntSymbolic):
            return str(value.compute_fn())
        elif isinstance(value, llarena.RoundedUpForAllocation):
            size = ('select(i1 icmp sgt({minsize.TV}, {basesize.TV}), '
                    '{minsize.TV}, {basesize.TV})'
                            .format(minsize=get_repr(value.minsize),
                                    basesize=get_repr(value.basesize)))
            return 'and({T} add({T} {}, {T} {}), {T} {})'.format(
                    size, align-1, ~(align-1), T=SIGNED_TYPE)
        elif isinstance(value, llmemory.GCHeaderOffset):
            return '0'
        elif isinstance(value, llmemory.CompositeOffset):
            x = self.repr_value(value.offsets[0])
            for offset in value.offsets[1:]:
                x = 'add({} {}, {})'.format(self.repr_type(), x,
                                            self.repr_type_and_value(offset))
            return x
        elif isinstance(value, llmemory.AddressOffset):
            if (isinstance(value, llmemory.ItemOffset) and
                isinstance(value.TYPE, lltype.OpaqueType) and
                value.TYPE.hints.get('external') == 'C'):
                return value.TYPE.hints['getsize']() * value.repeat
            indices = []
            to = self.add_offset_indices(indices, value)
            if to is lltype.Void:
                return '0'
            return 'ptrtoint({}* getelementptr({}, {}* null, {}) to {})'.format(
                    database.get_type(to).repr_type(),
                    database.get_type(value.TYPE).repr_type(),
                    database.get_type(value.TYPE).repr_type(),
                    ', '.join(indices), SIGNED_TYPE)
        elif isinstance(value, llgroup.GroupMemberOffset):
            grptype = database.get_type(value.grpptr._T).repr_type()
            grpptr = get_repr(value.grpptr)
            grpptr.type.to.write_group(grpptr.value._obj)
            member = get_repr(value.member)
            return ('ptrtoint({member.T} getelementptr({grptype}, '
                    '{grpptr.T} null, {} 0, i32 {value.index}) to {})'
                    .format(SIGNED_TYPE, LLVMHalfWord.repr_type(),
                            **locals()))
        elif isinstance(value, llgroup.CombinedSymbolic):
            T = SIGNED_TYPE
            lp = get_repr(value.lowpart)
            rest = get_repr(value.rest)
            return 'or({T} sext({lp.TV} to {T}), {rest.TV})'.format(**locals())
        elif isinstance(value, CDefinedIntSymbolic):
            if value is malloc_zero_filled:
                gctransformer = database.genllvm.gcpolicy.gctransformer
                return str(int(gctransformer.malloc_zero_filled))
            elif value is _we_are_jitted:
                return '0'
            elif value.expr.startswith('RPY_TLOFS_'):
                fieldname = value.expr[10:]
                idx = database.tls_struct.fldnames_wo_voids.index(fieldname)
                return ('ptrtoint({}* getelementptr({}, {}* null, i64 0, '
                        'i32 {}) to {})'.format(
                        database.tls_struct.fldtypes_wo_voids[idx].repr_type(),
                        database.tls_struct.repr_type(),
                        database.tls_struct.repr_type(), idx, SIGNED_TYPE))
        elif isinstance(value, llmemory.AddressAsInt):
            return 'ptrtoint({.TV} to {})'.format(get_repr(value.adr.ptr),
                                                  SIGNED_TYPE)
        elif isinstance(value, rffi.CConstant):
            # XXX HACK
            from rpython.rtyper.tool import rffi_platform
            return rffi_platform.getconstantinteger(
                    value.c_name,
                    '#include "/usr/include/curses.h"')
        raise NotImplementedError(value)

    def add_offset_indices(self, indices, offset):
        if isinstance(offset, llmemory.ItemOffset):
            indices.append('i64 {}'.format(offset.repeat))
            return offset.TYPE
        if not indices:
            indices.append('i64 0')
        if isinstance(offset, llmemory.FieldOffset):
            type = database.get_type(offset.TYPE)
            if isinstance(type, BareArrayType):
                assert offset.fldname.startswith('item')
                indices.append('i32 {}'.format(int(offset.fldname[4:])))
                return offset.TYPE.OF
            else:
                indices.append('i32 {}'.format(
                        type.fldnames_wo_voids.index(offset.fldname)))
                return offset.TYPE._flds[offset.fldname]
        if isinstance(offset, llmemory.ArrayLengthOffset):
            if offset.TYPE._gckind == 'gc':
                indices.append('i32 1')
            else:
                indices.append('i32 0')
            return lltype.Signed
        if isinstance(offset, llmemory.ArrayItemsOffset):
            if not offset.TYPE._hints.get("nolength", False):
                if offset.TYPE._gckind == 'gc':
                    indices.append('i32 2')
                else:
                    indices.append('i32 1')
            return lltype.FixedSizeArray(offset.TYPE.OF, 0)
        raise NotImplementedError

    def get_cast_op(self, to):
        if isinstance(to, IntegralType):
            if self.bitwidth > to.bitwidth:
                return 'trunc'
            elif self.bitwidth < to.bitwidth:
                if self.unsigned:
                    return 'zext'
                else:
                    return 'sext'
        elif isinstance(to, FloatType):
                if self.unsigned:
                    return 'uitofp'
                else:
                    return 'sitofp'
        elif isinstance(to, BasePtrType):
            return 'inttoptr'
        return 'bitcast'

    def __hash__(self):
        return 257 * self.unsigned + self.bitwidth

    def __eq__(self, other):
        if not isinstance(other, IntegralType):
            return False
        return (self.bitwidth == other.bitwidth and
                self.unsigned == other.unsigned)

    def __ne__(self, other):
        if not isinstance(other, IntegralType):
            return True
        return (self.bitwidth != other.bitwidth or
                self.unsigned != other.unsigned)


class BoolType(IntegralType):
    def __init__(self):
        IntegralType.__init__(self, 1, True)

    def is_zero(self, value):
        return not value

    def repr_value(self, value, extra_len=None):
        if value:
            return 'true'
        return 'false'


class FloatType(Type):
    def __init__(self, typestr, bitwidth):
        self.typestr = typestr
        self.bitwidth = bitwidth

    def is_zero(self, value):
        return float(value) == 0.0

    def repr_value(self, value, extra_len=None):
        if self.typestr == 'x86_fp80':
            import struct
            packed = struct.pack(">d", value)
            return "0xK" + ''.join([('{:02x}'.format(ord(i))) for i in packed])
        from rpython.rlib.rfloat import isinf, isnan
        if isinf(value) or isnan(value):
            import struct
            packed = struct.pack(">d", value)
            return "0x" + ''.join([('{:02x}'.format(ord(i))) for i in packed])
        ret = repr(float(value))
        # llvm requires a . when using e notation
        if "e" in ret and "." not in ret:
            return ret.replace("e", ".0e")
        return ret

    def get_cast_op(self, to):
        if isinstance(to, FloatType):
            if self.bitwidth > to.bitwidth:
                return 'fptrunc'
            elif self.bitwidth < to.bitwidth:
                return 'fpext'
        elif isinstance(to, IntegralType):
                if to.unsigned:
                    return 'fptoui'
                else:
                    return 'fptosi'
        return 'bitcast'


class BasePtrType(Type):
    def get_cast_op(self, to):
        if isinstance(to, IntegralType):
            return 'ptrtoint'
        return 'bitcast'


class AddressType(BasePtrType):
    typestr = 'i8*'

    def repr_of_type(self):
        return 'address'

    def is_zero(self, value):
        return value.ptr is None

    def repr_value(self, value, extra_len=None):
        if value.ptr is None:
            return 'null'
        return "bitcast({ptr.TV} to i8*)".format(ptr=get_repr(value.ptr))


LLVMVoid = VoidType()
LLVMBool = BoolType()
LLVMAddress = AddressType()
PRIMITIVES = {
    lltype.Void: LLVMVoid,
    lltype.Bool: LLVMBool,
    lltype.Float: FloatType('double', 64),
    lltype.SingleFloat: FloatType('float', 32),
    lltype.LongFloat: FloatType('x86_fp80', 80),
    llmemory.Address: LLVMAddress,
}

for type in rffi.NUMBER_TYPES + [lltype.Char, lltype.UniChar]:
    if type not in PRIMITIVES:
        size_in_bytes, is_unsigned = rffi.size_and_sign(type)
        PRIMITIVES[type] = IntegralType(size_in_bytes * 8, is_unsigned)
for key, value in PRIMITIVES.items():
    value.lltype = key
LLVMSigned = PRIMITIVES[lltype.Signed]
SIGNED_TYPE = LLVMSigned.repr_type()
LLVMHalfWord = PRIMITIVES[llgroup.HALFWORD]
LLVMInt = PRIMITIVES[rffi.INT]
LLVMChar = PRIMITIVES[lltype.Char]


class PtrType(BasePtrType):
    def __init__(self):
        self.refs = {None: 'null'}

    @classmethod
    def tmp(cls, to):
        # call __new__ to prevent __init__ from being called
        self = cls.__new__(cls)
        self.to = to
        return self

    def setup_from_lltype(self, db, type):
        self.to = db.get_type(type.TO)

    def repr_type(self, extra_len=None):
        return self.to.repr_type(extra_len) + '*'

    def repr_of_type(self):
        if not hasattr(self, 'to'):
            return 'self'
        return self.to.repr_of_type() + '_ptr'

    def is_zero(self, value):
        return not value

    def repr_value(self, value, extra_len=None):
        if value is COMPILER_INFO:
            return database.compiler_info
        obj = value._obj
        if isinstance(obj, int):
            return 'inttoptr({} {} to {})'.format(SIGNED_TYPE, obj,
                                                  self.repr_type())
        try:
            return self.refs[obj]
        except KeyError:
            p, c = lltype.parentlink(obj)
            if p:
                parent_type = database.get_type(p._TYPE)
                parent_ptr_type = database.get_type(lltype.Ptr(p._TYPE))
                parent_ref = parent_ptr_type.repr_type_and_value(p._as_ptr())
                if isinstance(c, str):
                    child = ConstantRepr(LLVMVoid, c)
                else:
                    child = get_repr(c)

                gep = GEP(None, None)
                to = parent_type.add_indices(gep, child)
                self.refs[obj] = (
                        'bitcast({} getelementptr inbounds({}, {}, {}) to {})'
                        .format(PtrType.tmp(to).repr_type(),
                                parent_type.repr_type(), parent_ref,
                                ', '.join(gep.indices), self.repr_type()))
            else:
                self.to.repr_ref(self, obj)
            return self.refs[obj]


class StructType(Type):
    def setup(self, name, fields, needs_gc_header):
        self.name = name
        self.needs_gc_header = needs_gc_header
        fields = list(fields)
        if needs_gc_header:
            header_type = database.genllvm.gcpolicy.gctransformer.HDR
            fields.insert(0, (database.get_type(header_type), '_gc_header'))
        elif all(t is LLVMVoid for t, f in fields):
            fields.append((LLVMSigned, '_fill'))
        self.fields = fields
        self.fldtypes_wo_voids = [t for t, f in fields if t is not LLVMVoid]
        self.fldnames_wo_voids = [f for t, f in fields if t is not LLVMVoid]
        self.fldnames_voids = set(f for t, f in fields if t is LLVMVoid)
        self.varsize = fields[-1][0].varsize
        self.size_variants = {}

    def setup_from_lltype(self, db, type):
        if (type._hints.get('typeptr', False) and
            db.genllvm.translator.config.translation.gcremovetypeptr):
            self.setup(type._name, [], True)
            return
        fields = ((db.get_type(type._flds[f]), f) for f in type._names)
        is_gc = type._gckind == 'gc'
        needs_gc_header = is_gc and type._first_struct() == (None, None)
        self.setup(type._name, fields, needs_gc_header)

    def repr_type(self, extra_len=None):
        if extra_len not in self.size_variants:
            if extra_len is not None:
                name = '%{}_plus_{}'.format(self.name, extra_len)
            elif self.varsize:
                name = '%{}_varsize'.format(self.name)
            else:
                name = '%{}'.format(self.name)
            self.size_variants[extra_len] = name = database.unique_name(name)
            lastname = self.fldnames_wo_voids[-1]
            tmp = ('    {semicolon}{fldtype}{comma} ; {fldname}\n'.format(
                           semicolon=';' if fldtype is LLVMVoid else '',
                           fldtype=fldtype.repr_type(extra_len),
                           comma=',' if fldname is not lastname else '',
                           fldname=fldname)
                   for fldtype, fldname in self.fields)
            database.f.write('{} = type {{\n{}}}\n'.format(name, ''.join(tmp)))
        return self.size_variants[extra_len]

    def repr_of_type(self):
        return self.name

    def is_zero(self, value):
        if self.needs_gc_header:
            return False
        elif self.fldnames_wo_voids == ['_fill']:
            return True
        return all(ft.is_zero(getattr(value, fn)) for ft, fn in self.fields)

    def get_extra_len(self, value):
        last_fldtype, last_fldname = self.fields[-1]
        return last_fldtype.get_extra_len(getattr(value, last_fldname))

    def repr_value(self, value, extra_len=None):
        if self.is_zero(value):
            return 'zeroinitializer'
        if self.needs_gc_header:
            gctransformer = database.genllvm.gcpolicy.gctransformer
            data = [gctransformer.gcheader_initdata(value)]
            data.extend(getattr(value, fn) for _, fn in self.fields[1:])
        else:
            data = [getattr(value, fn) for _, fn in self.fields]
        lastname = self.fldnames_wo_voids[-1]
        tmp = ('    {semicolon}{fldtype} {fldvalue}{comma} ; {fldname}'.format(
                       semicolon=';' if fldtype is LLVMVoid else '',
                       fldtype=fldtype.repr_type(extra_len),
                       fldvalue=fldtype.repr_value(fldvalue, extra_len)
                               .replace('\n', '\n    '),
                       comma=',' if fldname is not lastname else '',
                       fldname=fldname)
               for (fldtype, fldname), fldvalue in zip(self.fields, data))
        return '{{\n{}\n}}'.format('\n'.join(tmp))

    def add_indices(self, gep, attr):
        if attr.value in self.fldnames_voids:
            raise VoidAttributeAccess
        index = self.fldnames_wo_voids.index(attr.value)
        gep.add_field_index(index)
        return self.fldtypes_wo_voids[index]


class BareArrayType(Type):
    def setup(self, of, length):
        self.of = of
        self.length = length

    def setup_from_lltype(self, db, type):
        self.setup(db.get_type(type.OF), getattr(type, 'length', None))

    def repr_type(self, extra_len=None):
        if self.of is LLVMVoid:
            return '[0 x {}]'
        if extra_len is not None:
            return '[{} x {}]'.format(extra_len, self.of.repr_type())
        elif self.length is None:
            return '[0 x {}]'.format(self.of.repr_type())
        return '[{} x {}]'.format(self.length, self.of.repr_type())

    def repr_of_type(self):
        return 'array_of_' + self.of.repr_of_type()

    @property
    def varsize(self):
        return self.length is None

    def is_zero(self, value):
        if isinstance(value, _array_mixin):
            items = [value.getitem(i) for i in xrange(len(value.items))]
        else:
            items = value.items
        return all(self.of.is_zero(item) for item in items)

    def get_extra_len(self, value):
        try:
            return value.getlength()
        except AttributeError:
            assert isinstance(self.of, IntegralType)
            for i in count():
                if value.getitem(i) == '\00':
                    return i + 1

    def repr_value(self, value, extra_len=None):
        if isinstance(value, _array_mixin):
            items = [value.getitem(i) for i in xrange(len(value.items))]
        else:
            items = value.items
        if self.is_zero(value):
            return 'zeroinitializer'
        if self.of is LLVMChar:
            return 'c"{}"'.format(''.join(i if (32 <= ord(i) <= 126 and
                                                i != '"' and i != '\\')
                                          else r'\{:02x}'.format(ord(i))
                                  for i in items))
        return '[\n    {}\n]'.format(', '.join(
                self.of.repr_type_and_value(item) for item in items))

    def add_indices(self, gep, key):
        if key.type is LLVMVoid:
            index = int(key.value[4:])
        else:
            index = key.V
        gep.add_array_index(index)
        return self.of


class ArrayHelper(object):
    def __init__(self, value):
        self.len = value.getlength()
        self.items = value

    def _parentstructure(self):
        return self.items

class ArrayType(Type):
    varsize = True

    def setup(self, of, is_gc):
        self.needs_gc_header = is_gc
        self.bare_array_type = BareArrayType()
        self.bare_array_type.setup(of, None)
        self.struct_type = StructType()
        fields = [(LLVMSigned, 'len'), (self.bare_array_type, 'items')]
        self.struct_type.setup('array_of_' + of.repr_of_type(), fields, is_gc)

    def setup_from_lltype(self, db, type):
        self.setup(db.get_type(type.OF), type._gckind == 'gc')

    def repr_type(self, extra_len=None):
        return self.struct_type.repr_type(extra_len)

    def repr_of_type(self):
        return self.struct_type.repr_of_type()

    def is_zero(self, value):
        return self.struct_type.is_zero(ArrayHelper(value))

    def get_extra_len(self, value):
        return self.struct_type.get_extra_len(ArrayHelper(value))

    def repr_value(self, value, extra_len=None):
        return self.struct_type.repr_value(ArrayHelper(value), extra_len)

    def repr_type_and_value(self, value):
        return self.struct_type.repr_type_and_value(ArrayHelper(value))

    def add_indices(self, gep, index):
        if self.needs_gc_header:
            gep.add_field_index(2)
        else:
            gep.add_field_index(1)
        return self.bare_array_type.add_indices(gep, index)


class Group(object):
    pass


class GroupType(Type):
    def __init__(self):
        self.written = None

    def setup_from_lltype(self, db, type):
        self.typestr = '%group_' + type.name

    def repr_ref(self, ptr_type, obj):
        ptr_type.refs[obj] = '@group_' + obj.name

    def write_group(self, obj):
        if self.written is not None:
            assert self.written == obj.members
            return
        self.written = list(obj.members)
        groupname = '@group_' + obj.name
        group = Group()
        fields = []
        for i, member in enumerate(obj.members):
            fldname = 'member{}'.format(i)
            fields.append((database.get_type(member._TYPE), fldname))
            setattr(group, fldname, member)
            member_ptr_refs = database.get_type(lltype.Ptr(member._TYPE)).refs
            member_ptr_refs[member] = (
                    'getelementptr inbounds({}, {}* {}, i64 0, i32 {})'
                    .format(self.typestr, self.typestr, groupname, i))
        struct_type = StructType()
        struct_type.setup('group_' + obj.name, fields, False)
        database.f.write('{} = constant {}\n'.format(
                groupname, struct_type.repr_type_and_value(group)))


class FuncType(Type):
    def setup_from_lltype(self, db, type):
        self.result = db.get_type(type.RESULT)
        self.args = [db.get_type(argtype) for argtype in type.ARGS
                     if argtype is not lltype.Void]

    def repr_type(self, extra_len=None):
        return '{} ({})'.format(self.result.repr_type(),
                                ', '.join(arg.repr_type()
                                          for arg in self.args))

    def repr_of_type(self):
        return 'func'

    def repr_ref(self, ptr_type, obj):
        if getattr(obj, 'external', None) == 'C':
            if obj._name.startswith('llvm'):
                name = '@' + obj._name
            else:
                wrapper_name, source = rffi._write_call_wrapper(
                        obj._name, database.unique_name(obj._name, False),
                        obj._TYPE, 'RPY_EXTERN ')
                name = '@' + wrapper_name
                database.genllvm.sources.append(source)

            ptr_type.refs[obj] = name
            database.f.write('declare {} {}({})\n'.format(
                    self.result.repr_type(), name,
                    ', '.join(arg.repr_type() for arg in self.args)))
            database.genllvm.ecis.append(obj.compilation_info)
        else:
            if hasattr(getattr(obj, '_callable', None), 'c_name'):
                name = '@' + obj._callable.c_name
            else:
                name = database.unique_name('@rpy_' + obj._name)
            ptr_type.refs[obj] = name
            if hasattr(obj, 'graph'):
                writer = FunctionWriter()
                writer.write_graph(ptr_type, name, obj.graph,
                                   obj in database.genllvm.entrypoints)
                database.f.writelines(writer.lines)


class OpaqueType(Type):
    typestr = 'i8'

    def repr_of_type(self):
        return 'opaque'

    def is_zero(self, value):
        raise ValueError("value is opaque")

    def repr_ref(self, ptr_type, obj):
        if hasattr(obj, 'container'):
            realvalue = get_repr(lltype.cast_opaque_ptr(
                    lltype.Ptr(lltype.typeOf(obj.container)), obj._as_ptr()))
            ptr_type.refs[obj] = 'bitcast({.TV} to i8*)'.format(realvalue)
        else:
            raise ValueError("value is opaque")


class WeakRefType(Type):
    def setup_from_lltype(self, db, type):
        self.struct_type = StructType()
        self.struct_type.setup_from_lltype(db, WEAKREF)

    def repr_type(self, extra_len=None):
        return self.struct_type.repr_type(extra_len)

    def repr_of_type(self):
        return 'weakref'

    def is_zero(self, value):
        return self.struct_type.is_zero(value._converted_weakref)

    def repr_value(self, value):
        return self.struct_type.repr_value(value._converted_weakref)


_LL_TO_LLVM = {
    lltype.Ptr: PtrType,
    lltype.Struct: StructType, lltype.GcStruct: StructType,
    lltype.Array: ArrayType, lltype.GcArray: ArrayType,
    lltype.FixedSizeArray: BareArrayType,
    lltype.FuncType: FuncType,
    lltype.OpaqueType: OpaqueType, lltype.GcOpaqueType: OpaqueType,
    llgroup.GroupType: GroupType,
    llmemory._WeakRefType: WeakRefType,
}

class Database(object):
    identifier_regex = re.compile('^[%@][a-zA-Z$._][a-zA-Z$._0-9]*$')

    def __init__(self, genllvm, f):
        self.genllvm = genllvm
        self.f = f
        self.names_counter = {}
        self.types = PRIMITIVES.copy()
        self.stack_bottoms = []
        self.tls_getters = set()
        self.tls_addr_wrapper = False

    def get_type(self, type):
        try:
            return self.types[type]
        except KeyError:
            if isinstance(type, lltype.Typedef):
                return self.get_type(type.OF)
            elif (isinstance(type, lltype.Array) and
                  type._hints.get('nolength', False)):
                class_ = BareArrayType
            elif type is lltype.RuntimeTypeInfo:
                class_ = self.genllvm.gcpolicy.RttiType
            else:
                class_ = _LL_TO_LLVM[type.__class__]
            self.types[type] = ret = class_()
            ret.setup_from_lltype(self, type)
            if ret.needs_gc_header:
                gctransformer = database.genllvm.gcpolicy.gctransformer
                _llvm_needs_header[type] = [(gctransformer.HDR, '_gc_header')]
            ret.lltype = type
            return ret

    def unique_name(self, name, llvm_name=True):
        if name not in self.names_counter:
            self.names_counter[name] = 0
            if llvm_name and self.identifier_regex.match(name) is None:
                return '{}"{}"'.format(name[0], name[1:])
            return name
        self.names_counter[name] += 1
        return self.unique_name('{}_{}'.format(name, self.names_counter[name]),
                                llvm_name)


def _setup_binary_ops():
    ops = {}

    # arithmetic
    for type in ['int', 'uint', 'llong', 'ullong', 'lllong']:
        ops[type + '_lshift'] = 'shl'
        ops[type + '_rshift'] = 'lshr' if type[0] == 'u' else 'ashr'
        ops[type + '_add'] = 'add' if type[0] == 'u' else 'add nsw'
        ops[type + '_sub'] = 'sub' if type[0] == 'u' else 'sub nsw'
        ops[type + '_mul'] = 'mul' if type[0] == 'u' else 'mul nsw'
        ops[type + '_floordiv'] = 'udiv' if type[0] == 'u' else 'sdiv'
        ops[type + '_mod'] = 'urem' if type[0] == 'u' else 'srem'
        for op in ['and', 'or', 'xor']:
            ops['{}_{}'.format(type, op)] = op
    for type in ['float']:
        for op in ['add', 'sub', 'mul']:
            ops['{}_{}'.format(type, op)] = 'f' + op
        ops['{}_truediv'.format(type)] = 'fdiv'

    # comparisons
    for type, prefix in [('char', 'u'), ('unichar', 'u'), ('int', 's'),
                         ('uint', 'u'), ('llong', 's'), ('ullong', 'u'),
                         ('lllong', 's'), ('adr', 's'), ('ptr', 's')]:
        ops[type + '_eq'] = 'icmp eq'
        ops[type + '_ne'] = 'icmp ne'
        for op in ['gt', 'ge', 'lt', 'le']:
            ops['{}_{}'.format(type, op)] = 'icmp {}{}'.format(prefix, op)
    for type in ['float']:
        ops[type + '_ne'] = 'fcmp une'
        for op in ['eq', 'gt', 'ge', 'lt', 'le']:
            ops['{}_{}'.format(type, op)] = 'fcmp o' + op

    return ops

BINARY_OPS = _setup_binary_ops()


class ConstantRepr(object):
    def __init__(self, type, value):
        self.type = type
        self.value = value

    @property
    def T(self):
        return self.type.repr_type()

    @property
    def V(self):
        return self.type.repr_value(self.value)

    @property
    def TV(self):
        return self.type.repr_type_and_value(self.value)

    def __repr__(self):
        return '<{} {}>'.format(self.type.repr_type(), self.value)


class VariableRepr(object):
    def __init__(self, type, name):
        self.type = type
        self.name = name

    @property
    def T(self):
        return self.type.repr_type()

    @property
    def V(self):
        return self.name

    @property
    def TV(self):
        return '{} {}'.format(self.type.repr_type(), self.name)

    def __repr__(self):
        return '<{} {}>'.format(self.type.repr_type(), self.name)


def get_repr(cov):
    if isinstance(cov, Constant):
        return ConstantRepr(database.get_type(cov.concretetype), cov.value)
    elif isinstance(cov, Variable):
        return VariableRepr(database.get_type(cov.concretetype), '%'+cov.name)
    return ConstantRepr(database.get_type(lltype.typeOf(cov)), cov)


class VoidAttributeAccess(Exception):
    pass

class GEP(object):
    def __init__(self, func_writer, ptr):
        self.func_writer = func_writer
        self.ptr = ptr
        self.indices = ['{} 0'.format(SIGNED_TYPE)]

    def add_array_index(self, index):
        self.indices.append('{} {}'.format(SIGNED_TYPE, index))

    def add_field_index(self, index):
        self.indices.append('i32 {}'.format(index))

    def assign(self, result):
        fmt = '{result.V} = getelementptr inbounds {type}, {ptr.TV}, {indices}'
        self.func_writer.w(fmt.format(result=result, ptr=self.ptr,
                                      type=self.ptr.type.to.repr_type(),
                                      indices=', '.join(self.indices)))


def _var_eq(res, inc):
    return (isinstance(inc, Variable) and
            inc._name == res._name and
            inc._nr == res._nr)

class FunctionWriter(object):
    def __init__(self):
        self.lines = []
        self.tmp_counter = count()
        self.need_badswitch_block = False

    def w(self, line, indent='    '):
        self.lines.append('{}{}\n'.format(indent, line))

    def write_graph(self, ptr_type, name, graph, export):
        prevent_inline, llvmgcroot = self.prepare_graph(ptr_type, name, graph)
        self.w('define {linkage}{retvar.T} {name}({a}) {attrs}{gc} {{'.format(
                       linkage='' if export else 'internal ',
                       retvar=get_repr(graph.getreturnvar()),
                       name=name,
                       a=', '.join(get_repr(arg).TV for arg in graph.getargs()
                                   if arg.concretetype is not lltype.Void),
                       attrs=database.target_attributes +
                             (' noinline' if prevent_inline else ''),
                       gc=' gc "pypy"' if llvmgcroot else ''),
               '')

        self.entrymap = mkentrymap(graph)
        self.block_to_name = {}
        for i, block in enumerate(graph.iterblocks()):
            self.block_to_name[block] = 'block{}'.format(i)

        for block in graph.iterblocks():
            self.w(self.block_to_name[block] + ':', '  ')
            if block is not graph.startblock:
                self.write_phi_nodes(block)
            self.write_operations(block)
            self.write_branches(block)
        if self.need_badswitch_block:
            self.w('badswitch:', '  ')
            self.w('call void @abort() noreturn nounwind')
            self.w('unreachable')
        self.w('}', '')

    def prepare_graph(self, ptr_type, name, graph):
        genllvm = database.genllvm
        remove_same_as(graph)

        llvmgcroot = genllvm.translator.config.translation.gcrootfinder == \
                'llvmgcroot'
        if llvmgcroot:
            raise NotImplementedError
            try:
                prevent_inline = graph.func._gctransformer_hint_close_stack_
            except AttributeError:
                prevent_inline = (name == '@rpy_walk_stack_roots' or
                                  name.startswith('@rpy_stack_check'))
        else:
            self.transform_gc_reload_possibly_moved(graph)
            prevent_inline = False

        remove_double_links(graph)
        no_links_to_startblock(graph)
        SSI_to_SSA(graph)
        return prevent_inline, llvmgcroot

    def transform_gc_reload_possibly_moved(self, graph):
        for block in graph.iterblocks():
            rename = {}
            for op in block.operations:
                if rename:
                    op.args = [rename.get(v, v) for v in op.args]
                if op.opname == 'gc_reload_possibly_moved':
                    v_newaddr, v_targetvar = op.args
                    assert isinstance(v_targetvar.concretetype, lltype.Ptr)
                    v_newptr = Variable()
                    v_newptr.concretetype = v_targetvar.concretetype
                    op.opname = 'cast_adr_to_ptr'
                    op.args = [v_newaddr]
                    op.result = v_newptr
                    rename[v_targetvar] = v_newptr
            if rename:
                block.exitswitch = rename.get(block.exitswitch,
                                              block.exitswitch)
                for link in block.exits:
                    link.args = [rename.get(v, v) for v in link.args]

    def write_phi_nodes(self, block):
        for i, arg in enumerate(block.inputargs):
            if (arg.concretetype == lltype.Void or
                all(_var_eq(arg, l.args[i]) for l in self.entrymap[block])):
                continue
            s = ', '.join('[{}, %{}]'.format(
                        get_repr(l.args[i]).V, self.block_to_name[l.prevblock])
                    for l in self.entrymap[block] if l.prevblock is not None)
            self.w('{arg.V} = phi {arg.T} {s}'.format(arg=get_repr(arg), s=s))

    def write_branches(self, block):
        if len(block.exits) == 0:
            ret = block.inputargs[0]
            if ret.concretetype is lltype.Void:
                self.w('ret void')
            else:
                self.w('ret {ret.TV}'.format(ret=get_repr(ret)))
        elif len(block.exits) == 1:
            self.w('br label %' + self.block_to_name[block.exits[0].target])
        elif block.exitswitch.concretetype is lltype.Bool:
            assert len(block.exits) == 2
            true = block.exits[block.exits[1].llexitcase].target
            false = block.exits[block.exits[0].llexitcase].target
            self.w('br i1 {}, label %{}, label %{}'.format(
                    get_repr(block.exitswitch).V, self.block_to_name[true],
                    self.block_to_name[false]))
        else:
            default = None
            destinations = []
            for link in block.exits:
                if link.llexitcase is None:
                    default = self.block_to_name[link.target]
                else:
                    destinations.append((get_repr(link.llexitcase),
                                         self.block_to_name[link.target]))
            if default is None:
                default = 'badswitch'
                self.need_badswitch_block = True
            self.w('switch {}, label %{} [ {} ]'.format(
                    get_repr(block.exitswitch).TV,
                    default, ' '.join('{}, label %{}'.format(val.TV, dest)
                                      for val, dest in destinations)))

    def write_operations(self, block):
        for op in block.operations:
            self.w('; {}'.format(op))
            opname = op.opname
            opres = get_repr(op.result)
            opargs = [get_repr(arg) for arg in op.args]
            if opname in BINARY_OPS:
                binary_op = BINARY_OPS[opname]
                assert len(opargs) == 2
                if ((opargs[0].type != opargs[1].type) and
                    (opargs[0].type.bitwidth != opargs[1].type.bitwidth) and
                    isinstance(opargs[1], VariableRepr)):
                    assert binary_op in ('shl', 'lshr', 'ashr')
                    t = self._tmp()
                    self.w('{t.V} = sext {opargs[1].TV} to {opargs[0].T}'
                            .format(**locals()))
                    opargs[1] = t
                self.w('{opres.V} = {binary_op} {opargs[0].TV}, {opargs[1].V}'
                        .format(**locals()))
            elif opname.startswith('cast_') or opname.startswith('truncate_'):
                self._cast(opres, opargs[0])
            else:
                func = getattr(self, 'op_' + opname, None)
                if func is not None:
                    try:
                        func(opres, *opargs)
                    except VoidAttributeAccess:
                        pass
                else:
                    raise NotImplementedError(op)

    def _tmp(self, type=None):
        return VariableRepr(type, '%tmp{}'.format(next(self.tmp_counter)))

    def op_llvm_gcmap(self, result):
        self.w('{result.V} = bitcast i8* @__gcmap to {result.T}'
                .format(**locals()))

    def op_llvm_stack_malloc(self, result):
        type = result.type.to.repr_type()
        self.w('{result.V} = alloca {type}'.format(**locals()))

    # TODO: implement

    def op_have_debug_prints(self, result):
        self.w('{result.V} = bitcast i1 false to i1'.format(**locals()))

    def op_have_debug_prints_for(self, result, category_prefix):
        self.w('{result.V} = bitcast i1 false to i1'.format(**locals()))

    def op_ll_read_timestamp(self, result):
        self.op_direct_call(result, get_repr(llvm_readcyclecounter))

    def op_debug_print(self, result, *args):
        pass

    def op_debug_assert(self, result, *args):
        pass

    def op_debug_assert_not_none(self, result, *args):
        pass

    def op_debug_llinterpcall(self, result, *args):
        self.w('call void @abort() noreturn nounwind')
        if result.type is not LLVMVoid:
            self.w('{result.V} = bitcast {result.T} undef to {result.T}'
                    .format(**locals()))

    def op_debug_fatalerror(self, result, *args):
        self.w('call void @abort() noreturn nounwind')

    def op_debug_record_traceback(self, result, *args):
        pass

    def op_debug_start_traceback(self, result, *args):
        pass

    def op_debug_catch_exception(self, result, *args):
        pass

    def op_debug_reraise_traceback(self, result, *args):
        pass

    def op_debug_print_traceback(self, result):
        pass

    def op_debug_start(self, result, *args):
        pass

    def op_debug_stop(self, result, *args):
        pass

    def op_debug_nonnull_pointer(self, result, *args):
        pass

    def op_debug_offset(self, result, *args):
        pass

    def op_debug_flush(self, result, *args):
        pass

    def op_debug_forked(self, result, *args):
        pass

    def op_track_alloc_start(self, result, *args):
        pass

    def op_track_alloc_stop(self, result, *args):
        pass

    def _cast(self, to, fr):
        if fr.type is LLVMVoid:
            return
        elif fr.type is to.type:
            op = 'bitcast'
        elif to.type is LLVMBool:
            if isinstance(fr.type, IntegralType):
                self.w('{to.V} = icmp ne {fr.TV}, 0'.format(**locals()))
            elif isinstance(fr.type, FloatType):
                zer = ConstantRepr(fr.type, 0.0)
                self.w('{to.V} = fcmp une {fr.TV}, {zer.V}'.format(**locals()))
            else:
                raise NotImplementedError
            return
        else:
            op = fr.type.get_cast_op(to.type)
        self.w('{to.V} = {op} {fr.TV} to {to.T}'.format(**locals()))
    op_force_cast = _cast
    op_raw_malloc_usage = _cast

    def op_direct_call(self, result, fn, *args):
        if (isinstance(fn, ConstantRepr) and
            (fn.value._obj is None or fn.value._obj._name == 'PYPY_NO_OP')):
            return

        it = iter(fn.type.to.args)
        tmp = []
        for arg in args:
            if arg.type is LLVMVoid:
                continue
            argtype = next(it)
            if isinstance(argtype, StructType):
                t = self._tmp(argtype)
                self.w('{t.V} = load {t.T}, {arg.TV}'.format(**locals()))
                arg = t
            tmp.append('{arg.TV}'.format(arg=arg))
        args = ', '.join(tmp)

        tailmarker = ''
        try:
            if fn.value._obj.graph.inhibit_tail_call:
                tailmarker = 'notail '
        except AttributeError:
            pass

        if result.type is LLVMVoid:
            fmt = '{tailmarker}call void {fn.V}({args})'
        else:
            fmt = '{result.V} = {tailmarker}call {result.T} {fn.V}({args})'
        self.w(fmt.format(**locals()))
    op_indirect_call = op_direct_call

    def _get_element_ptr(self, ptr, fields, result):
        gep = GEP(self, ptr)
        type = ptr.type.to
        for field in fields:
            type = type.add_indices(gep, field)
        gep.assign(result)

    def _get_element_ptr_op(self, result, ptr, *fields):
        self._get_element_ptr(ptr, fields, result)
    op_getsubstruct = op_getarraysubstruct = _get_element_ptr_op

    def _get_element(self, result, var, *fields):
        if result.type is not LLVMVoid:
            if var.type.lltype.TO._hints.get('immutable'):
                metadata= ', !invariant.load !0'
            else:
                metadata=''
            t = self._tmp(PtrType.tmp(result.type))
            self._get_element_ptr(var, fields, t)
            self.w('{result.V} = load {result.T}, {t.TV}{metadata}'
                    .format(**locals()))
    op_getfield = op_bare_getfield = _get_element
    op_getinteriorfield = op_bare_getinteriorfield = _get_element
    op_getarrayitem = op_bare_getarrayitem = _get_element

    def _set_element(self, result, var, *rest):
        fields = rest[:-1]
        value = rest[-1]
        if value.type is not LLVMVoid:
            t = self._tmp(PtrType.tmp(value.type))
            self._get_element_ptr(var, fields, t)
            self.w('store {value.TV}, {t.TV}'.format(**locals()))
    op_setfield = op_bare_setfield = _set_element
    op_setinteriorfield = op_bare_setinteriorfield = _set_element
    op_setarrayitem = op_bare_setarrayitem = _set_element

    def op_direct_fieldptr(self, result, ptr, field):
        t = self._tmp(PtrType.tmp(result.type.to.of))
        self._get_element_ptr(ptr, [field], t)
        self.w('{result.V} = bitcast {t.TV} to {result.T}'.format(**locals()))

    def op_direct_arrayitems(self, result, ptr):
        t = self._tmp(PtrType.tmp(result.type.to.of))
        self._get_element_ptr(ptr, [ConstantRepr(LLVMSigned, 0)], t)
        self.w('{result.V} = bitcast {t.TV} to {result.T}'.format(**locals()))

    def op_direct_ptradd(self, result, var, val):
        t = self._tmp(PtrType.tmp(result.type.to.of))
        vt = var.type.to.repr_type()
        self.w('{t.V} = getelementptr inbounds {vt}, {var.TV}, i64 0, {val.TV}'
                .format(**locals()))
        self.w('{result.V} = bitcast {t.TV} to {result.T}'.format(**locals()))

    def op_getarraysize(self, result, ptr, *fields):
        gep = GEP(self, ptr)
        type = ptr.type.to
        for field in fields:
            type = type.add_indices(gep, field)

        if isinstance(type, BareArrayType):
            self.w('{result.V} = add {result.T} 0, {type.length}'
                    .format(**locals()))
        else:
            if type.needs_gc_header:
                gep.add_field_index(1)
            else:
                gep.add_field_index(0)
            t = self._tmp(PtrType.tmp(LLVMSigned))
            gep.assign(t)
            self.w('{result.V} = load {result.T}, {t.TV}'.format(**locals()))
    op_getinteriorarraysize = op_getarraysize

    def _is_true(self, result, var):
        self.w('{result.V} = icmp ne {var.TV}, 0'.format(**locals()))
    op_int_is_true = op_uint_is_true = _is_true
    op_llong_is_true = op_ullong_is_true = _is_true
    op_lllong_is_true = _is_true

    def _invert(self, result, var):
        self.w('{result.V} = xor {var.TV}, -1'.format(**locals()))
    op_int_invert = op_uint_invert = _invert
    op_llong_invert = op_ullong_invert = _invert
    op_bool_not = _invert

    def op_int_neg(self, result, var):
        self.w('{result.V} = sub {var.T} 0, {var.V}'.format(**locals()))
    op_llong_neg = op_int_neg

    def op_int_abs(self, result, var):
        ispos = self._tmp()
        neg = self._tmp(var.type)
        self.w('{ispos.V} = icmp sgt {var.TV}, -1'.format(**locals()))
        self.w('{neg.V} = sub {var.T} 0, {var.V}'.format(**locals()))
        self.w('{result.V} = select i1 {ispos.V}, {var.TV}, {neg.TV}'
                .format(**locals()))
    op_llong_abs = op_int_abs

    def _ovf_op(int_op):
        def f(self, result, x, y):
            t1 = self._tmp()
            t2 = self._tmp(LLVMBool)
            int_op # reference to include it in locals()
            T = SIGNED_TYPE
            self.w('{t1.V} = call {{{T}, i1}} @llvm.{int_op}.with.overflow.{T}'
                   '({x.TV}, {y.TV})'.format(**locals()))
            self.w('{result.V} = extractvalue {{{T}, i1}} {t1.V}, 0'
                    .format(**locals()))
            self.w('{t2.V} = extractvalue {{{T}, i1}} {t1.V}, 1'
                    .format(**locals()))
            self.w('call void @_raise_ovf({t2.TV})'.format(**locals()))
        return f
    op_int_add_ovf = op_int_add_nonneg_ovf = _ovf_op('sadd')
    op_int_sub_ovf = _ovf_op('ssub')
    op_int_mul_ovf = _ovf_op('smul')

    def op_int_between(self, result, a, b, c):
        t1 = self._tmp()
        t2 = self._tmp()
        self.w('{t1.V} = icmp sle {a.TV}, {b.V}'.format(**locals()))
        self.w('{t2.V} = icmp slt {b.TV}, {c.V}'.format(**locals()))
        self.w('{result.V} = and i1 {t1.V}, {t2.V}'.format(**locals()))

    def op_int_force_ge_zero(self, result, var):
        isneg = self._tmp()
        self.w('{isneg.V} = icmp slt {var.TV}, 0'.format(**locals()))
        self.w('{result.V} = select i1 {isneg.V}, {var.T} 0, {var.TV}'
                .format(**locals()))

    def op_ptr_iszero(self, result, var):
        self.w('{result.V} = icmp eq {var.TV}, null'.format(**locals()))

    def op_ptr_nonzero(self, result, var):
        self.w('{result.V} = icmp ne {var.TV}, null'.format(**locals()))

    def op_adr_delta(self, result, arg1, arg2):
        t1 = self._tmp(LLVMSigned)
        t2 = self._tmp(LLVMSigned)
        self.w('{t1.V} = ptrtoint {arg1.TV} to {t1.T}'.format(**locals()))
        self.w('{t2.V} = ptrtoint {arg2.TV} to {t2.T}'.format(**locals()))
        self.w('{result.V} = sub {t1.TV}, {t2.V}'.format(**locals()))

    def op_adr_add(self, result, addr, offset):
        self.w('{result.V} = getelementptr i8, {addr.TV}, {offset.TV}'
                .format(**locals()))

    def op_adr_sub(self, result, addr, offset):
        offset_neg = self._tmp(LLVMSigned)
        self.w('{offset_neg.V} = sub {offset.T} 0, {offset.V}'
                .format(**locals()))
        self.w('{result.V} = getelementptr i8, {addr.TV}, {offset_neg.TV}'
                .format(**locals()))

    def op_float_neg(self, result, var):
        self.w('{result.V} = fsub {var.T} -0.0, {var.V}'.format(**locals()))

    def op_float_abs(self, result, var):
        ispos = self._tmp()
        neg = self._tmp(var.type)
        self.w('{ispos.V} = fcmp oge {var.TV}, 0.0'.format(**locals()))
        self.w('{neg.V} = fsub {var.T} 0.0, {var.V}'.format(**locals()))
        self.w('{result.V} = select i1 {ispos.V}, {var.TV}, {neg.TV}'
                .format(**locals()))

    def op_float_is_true(self, result, var):
        self.w('{result.V} = fcmp one {var.TV}, 0.0'.format(**locals()))

    def op_raw_malloc(self, result, size, zero):
        if zero.value is True:
            self.op_direct_call(result, get_repr(raw_calloc), size,
                                ConstantRepr(LLVMInt, 1))
        elif zero.value is False:
            self.op_direct_call(result, get_repr(raw_malloc), size)
        else:
            assert False

    def op_raw_free(self, result, ptr):
        self.op_direct_call(result, get_repr(raw_free), ptr)

    def _get_addr(self, ptr_to, addr, offset):
        t1 = self._tmp(PtrType.tmp(LLVMChar))
        t2 = self._tmp(PtrType.tmp(LLVMChar))
        t3 = self._tmp(PtrType.tmp(ptr_to))
        self._cast(t1, addr)
        self.w('{t2.V} = getelementptr inbounds i8, {t1.TV}, {offset.TV}'
                .format(**locals()))
        self.w('{t3.V} = bitcast {t2.TV} to {t3.T}'.format(**locals()))
        return t3

    def op_raw_load(self, result, addr, offset):
        addr = self._get_addr(result.type, addr, offset)
        self.w('{result.V} = load {result.T}, {addr.TV}'.format(**locals()))

    def op_raw_store(self, result, addr, offset, value):
        addr = self._get_addr(value.type, addr, offset)
        self.w('store {value.TV}, {addr.TV}'.format(**locals()))
    op_bare_raw_store = op_raw_store

    def op_raw_memclear(self, result, ptr, size):
        self.op_direct_call(result, get_repr(llvm_memset), ptr, null_char,
                            size, null_int, null_bool)

    def op_raw_memset(self, result, ptr, val, size):
        assert 0 <= val.value <= 255
        self.op_direct_call(result, get_repr(llvm_memset), ptr,
                            ConstantRepr(LLVMChar, chr(val.value)),
                            size, null_int, null_bool)

    def op_raw_memcopy(self, result, src, dst, size):
        self.op_direct_call(result, get_repr(llvm_memcpy), dst, src, size,
                            null_int, null_bool)

    def op_extract_ushort(self, result, val):
        self.w('{result.V} = trunc {val.TV} to {result.T}'.format(**locals()))

    def op_is_group_member_nonzero(self, result, compactoffset):
        self.w('{result.V} = icmp ne {compactoffset.TV}, 0'.format(**locals()))

    def op_combine_ushort(self, result, ushort, rest):
        t = self._tmp(result.type)
        self.w('{t.V} = zext {ushort.TV} to {t.T}'.format(**locals()))
        self.w('{result.V} = or {t.TV}, {rest.V}'.format(**locals()))

    def op_get_group_member(self, result, groupptr, compactoffset):
        t1 = self._tmp(LLVMSigned)
        t2 = self._tmp(LLVMSigned)
        self.w('{t1.V} = zext {compactoffset.TV} to {t1.T}'.format(**locals()))
        self.w('{t2.V} = add {t1.TV}, ptrtoint({groupptr.TV} to {t1.T})'
                .format(**locals()))
        self.w('{result.V} = inttoptr {t2.TV} to {result.T}'
                .format(**locals()))

    def op_get_next_group_member(self, result, groupptr, compactoffset,
                                 skipoffset):
        t1 = self._tmp(LLVMSigned)
        t2 = self._tmp(LLVMSigned)
        t3 = self._tmp(LLVMSigned)
        self.w('{t1.V} = zext {compactoffset.TV} to {t1.T}'.format(**locals()))
        self.w('{t2.V} = add {t1.TV}, ptrtoint({groupptr.TV} to {t1.T})'
                .format(**locals()))
        self.w('{t3.V} = add {t2.TV}, {skipoffset.V}'.format(**locals()))
        self.w('{result.V} = inttoptr {t3.TV} to {result.T}'
                .format(**locals()))

    def op_gc_gettypeptr_group(self, result, obj, grpptr, skipoffset, vtinfo):
        t1 = self._tmp(LLVMSigned)
        t2 = self._tmp(LLVMHalfWord)
        self._get_element(t1, obj, ConstantRepr(LLVMVoid, '_gc_header'),
                          ConstantRepr(LLVMVoid, vtinfo.value[2]))
        self._cast(t2, t1)
        self.op_get_next_group_member(result, grpptr, t2, skipoffset)

    def op_gc_gcflag_extra(self, result, subopnum, obj=None):
        if subopnum.value == 1:
            self.w('{result.V} = and i1 true, true'.format(**locals()))
            return
        gctransformer = database.genllvm.gcpolicy.gctransformer
        gcflag_extra = get_repr(gctransformer.gcdata.gc.gcflag_extra)
        t1 = self._tmp(database.get_type(lltype.Ptr(gctransformer.HDR)))
        t2 = self._tmp(database.get_type(gctransformer.HDR._flds['tid']))
        t3 = self._tmp(database.get_type(gctransformer.HDR._flds['tid']))
        self._cast(t1, obj)
        self._get_element(t2, t1, ConstantRepr(LLVMVoid, 'tid'))
        if subopnum.value == 2:
            self.w('{t3.V} = and {t2.TV}, {gcflag_extra.V}'.format(**locals()))
            self._is_true(result, t3)
        elif subopnum.value == 3:
            self.w('{t3.V} = xor {t2.TV}, {gcflag_extra.V}'.format(**locals()))
            self._set_element(result, t1, ConstantRepr(LLVMVoid, 'tid'), t3)
        else:
            assert False, "No subop {}".format(subopnum.value)

    def op_gc_thread_run(self, result):
        self.op_direct_call(result, get_repr(rpy_threadlocalref_ensure))

    def op_gc_thread_die(self, result):
        self.op_direct_call(result, get_repr(rpy_tls_thread_die))

    def _ignore(self, *args):
        pass
    op_gc_stack_bottom = _ignore
    op_keepalive = _ignore
    op_jit_force_virtualizable = _ignore
    op_jit_force_quasi_immutable = _ignore
    op_jit_marker = _ignore
    op_jit_ffi_save_result = _ignore
    op_jit_conditional_call = _ignore
    op_gc__collect = _ignore

    def op_jit_force_virtual(self, result, x):
        self._cast(result, x)

    def op_jit_is_virtual(self, result, x):
        self.w('{result.V} = bitcast i1 false to i1'.format(**locals()))

    def op_stack_current(self, result):
        if result.type is LLVMAddress:
            self.op_direct_call(result, get_repr(llvm_frameaddress), null_int)
        else:
            t = self._tmp(LLVMAddress)
            self.op_direct_call(t, get_repr(llvm_frameaddress), null_int)
            self.w('{result.V} = ptrtoint {t.TV} to {result.T}'
                    .format(**locals()))

    def op_hint(self, result, var, hints):
        self._cast(result, var)

    def op_gc_call_rtti_destructor(self, result, rtti, addr):
        self.op_direct_call(result, rtti, addr)

    def op_gc_free(self, result, addr):
        self.op_raw_free(result, addr)

    def op_convert_float_bytes_to_longlong(self, result, fl):
        self.w('{result.V} = bitcast {fl.TV} to {result.T}'.format(**locals()))

    def op_convert_longlong_bytes_to_float(self, result, ll):
        self.w('{result.V} = bitcast {ll.TV} to {result.T}'.format(**locals()))

    def op_threadlocalref_get(self, result, offset):
        if isinstance(offset, ConstantRepr):
            assert isinstance(offset.value, CDefinedIntSymbolic)
            fieldname = offset.value.expr
            assert fieldname.startswith('RPY_TLOFS_')
            fieldname = fieldname[10:]
            if fieldname not in database.tls_getters:
                database.tls_getters.add(fieldname)
                from rpython.translator.c.database import LowLevelDatabase
                from rpython.translator.c.support import cdecl
                db = LowLevelDatabase()
                pattern = ("{}() {{ return RPY_THREADLOCALREF_GET({}); }}")
                database.genllvm.sources.append(pattern.format(
                        cdecl(db.gettype(result.type.lltype),
                              '_rpy_tls_get_' + fieldname), fieldname))
                database.f.write('declare {result.T} @_rpy_tls_get_{fieldname}()'
                        .format(**locals()))
            self.w('{result.V} = call {result.T} @_rpy_tls_get_{fieldname}()'
                    .format(**locals()))
        else:
            tls_addr = self._tmp(LLVMAddress)
            self.op_threadlocalref_addr(tls_addr)
            self.op_raw_load(result, tls_addr, offset)

    def op_threadlocalref_addr(self, result):
        if not database.tls_addr_wrapper:
            database.tls_addr_wrapper = True
            wrapper_src = ('char *_rpy_tls_addr() '
                           '{ char *r; OP_THREADLOCALREF_ADDR(r); return r; }')
            database.genllvm.sources.append(wrapper_src)
            database.f.write('declare i8* @_rpy_tls_addr()\n')
        self.w('{result.V} = call i8* @_rpy_tls_addr()'.format(**locals()))

    def op_likely(self, result, cond):
        self.w('{result.V} = bitcast {cond.TV} to {result.T}'.format(**locals()))

    def op_unlikely(self, result, cond):
        self.w('{result.V} = bitcast {cond.TV} to {result.T}'.format(**locals()))

    def op_length_of_simple_gcarray_from_opaque(self, result, ptr):
        array_type = ArrayType()
        array_type.setup(LLVMVoid, True)
        tmp = self._tmp(PtrType.tmp(array_type))
        self._cast(tmp, ptr)
        self.op_getarraysize(result, tmp)


class GCPolicy(object):
    def __init__(self, genllvm):
        self.genllvm = genllvm
        self._considered_constant = set()
        self.delayed_ptrs = False

    def transform_graph(self, graph):
        self.gctransformer.transform_graph(graph)
        for block in graph.iterblocks():
            for arg in block.inputargs:
                if isinstance(arg, Constant):
                    self._consider_constant(arg.concretetype, arg.value)
            for link in block.exits:
                for arg in link.args:
                    if isinstance(arg, Constant):
                        self._consider_constant(arg.concretetype, arg.value)
            for op in block.operations:
                for arg in op.args:
                    if isinstance(arg, Constant):
                        self._consider_constant(arg.concretetype, arg.value)

    def _consider_constant(self, type, value):
        if type is llmemory.Address:
            value = value.ptr
            type = lltype.typeOf(value)
        if isinstance(type, lltype.Ptr):
            type = type.TO
            try:
                value = value._obj
            except lltype.DelayedPointer:
                self.delayed_ptrs = True
                return
            except AttributeError:
                return
            if value is None:
                return
        if isinstance(type, lltype.ContainerType):
            if isinstance(value, int):
                return
            if value in self._considered_constant:
                return
            self._considered_constant.add(value)
            if (isinstance(type, lltype.Struct) and
                not isinstance(value, lltype._subarray)):
                for f in type._names:
                    self._consider_constant(type._flds[f], getattr(value, f))
            elif isinstance(type, lltype.Array):
                if isinstance(value, _array_mixin):
                    len_ = len(value.items)
                    items = [value.getitem(i) for i in xrange(len_)]
                else:
                    items = value.items
                for i in items:
                    self._consider_constant(type.OF, i)
            elif type is lltype.RuntimeTypeInfo:
                if isinstance(self.gctransformer, RefcountingGCTransformer):
                    self.gctransformer.static_deallocation_funcptr_for_type(
                            value.about)
            elif type is llmemory.GCREF.TO and hasattr(value, 'container'):
                self._consider_constant(value.ORIGTYPE.TO, value.container)
            elif type is llmemory.WeakRef:
                wrapper = convert_weakref_to(value._dereference())
                self._consider_constant(wrapper._TYPE, wrapper)
                value._converted_weakref = wrapper._obj
            self.gctransformer.consider_constant(type, value)

            p, c = lltype.parentlink(value)
            if p:
                self._consider_constant(lltype.typeOf(p), p)

    def get_setup_ptr(self):
        return None

    def finish(self):
        genllvm = self.genllvm
        while self.delayed_ptrs:
            self.gctransformer.finish_helpers()

            self.delayed_ptrs = False
            for graph in genllvm.translator.graphs:
                genllvm.transform_graph(graph)

            finish_tables = self.gctransformer.get_finish_tables()
            if hasattr(finish_tables, '__iter__'):
                for finish_table in finish_tables:
                    for dep in finish_table:
                        self._consider_constant(lltype.typeOf(dep), dep)
        self.gctransformer.inline_helpers_and_postprocess(
                genllvm.translator.graphs)


class FrameworkGCPolicy(GCPolicy):
    class RttiType(Type):
        typestr = '{}'

        def is_zero(self, value):
            return True

        def repr_ref(self, ptr_type, obj):
            ptr_type.refs[obj] = 'null'

    def __init__(self, genllvm):
        GCPolicy.__init__(self, genllvm)
        self.gctransformer = {
            'llvmgcroot': LLVMGcRootFrameworkGCTransformer,
            'shadowstack': ShadowStackFrameworkGCTransformer
        }[genllvm.translator.config.translation.gcrootfinder](
                genllvm.translator)

    def get_setup_ptr(self):
        return self.gctransformer.frameworkgc_setup_ptr.value


class RefcountGCPolicy(GCPolicy):
    class RttiType(FuncType):
        def setup_from_lltype(self, db, type):
            self.result = LLVMVoid
            self.args = [LLVMAddress]

        def repr_ref(self, ptr_type, obj):
            ptr = database.genllvm.gcpolicy.gctransformer\
                    .static_deallocation_funcptr_for_type(obj.about)
            FuncType.repr_ref(self, ptr_type, ptr._obj)
            ptr_type.refs[obj] = ptr_type.refs.pop(ptr._obj)

    def __init__(self, genllvm):
        GCPolicy.__init__(self, genllvm)
        self.gctransformer = RefcountingGCTransformer(genllvm.translator)


def extfunc(name, args, result, compilation_info):
    func_type = lltype.FuncType(args, result)
    return lltype.functionptr(func_type, name, external='C', calling_conv='c',
                              random_effects_on_gcobjs=False,
                              compilation_info=compilation_info)

eci = ExternalCompilationInfo()
raw_malloc = extfunc('malloc', [lltype.Signed], llmemory.Address, eci)
raw_calloc = extfunc('calloc', [lltype.Signed, lltype.Signed],
                     llmemory.Address, eci)
raw_free = extfunc('free', [llmemory.Address], lltype.Void, eci)
llvm_memcpy = extfunc('llvm.memcpy.p0i8.p0i8.i' + str(LLVMSigned.bitwidth),
                      [llmemory.Address, llmemory.Address, lltype.Signed,
                       rffi.INT, lltype.Bool], lltype.Void, eci)
llvm_memset = extfunc('llvm.memset.p0i8.i' + str(LLVMSigned.bitwidth),
                      [llmemory.Address, rffi.SIGNEDCHAR, lltype.Signed,
                       rffi.INT, lltype.Bool], lltype.Void, eci)
llvm_frameaddress = extfunc('llvm.frameaddress', [rffi.INT], llmemory.Address,
                            eci)
llvm_readcyclecounter = extfunc('llvm.readcyclecounter', [],
                                lltype.SignedLongLong, eci)
rpy_tls_program_init = extfunc('RPython_ThreadLocals_ProgramInit', [],
                               lltype.Void, eci)
rpy_threadlocalref_ensure = extfunc('RPY_THREADLOCALREF_ENSURE', [],
                                    lltype.Void, eci)
rpy_tls_thread_die = extfunc('RPython_ThreadLocals_ThreadDie', [], lltype.Void,
                             eci)
del eci

null_int = ConstantRepr(LLVMInt, 0)
null_char = ConstantRepr(LLVMChar, '\0')
null_bool = ConstantRepr(LLVMBool, 0)


class GenLLVM(object):
    def __init__(self, translator):
        # XXX refactor code to be less recursive
        import sys
        sys.setrecursionlimit(10000)

        self.translator = translator
        self.exctransformer = translator.getexceptiontransformer()
        self.gcpolicy = {
            'framework': FrameworkGCPolicy,
            'ref': RefcountGCPolicy
        }[translator.config.translation.gctransformer](self)
        self.transformed_graphs = set()
        self.sources = [str(py.code.Source(r'''
        void pypy_debug_catch_fatal_exception(void) {
            fprintf(stderr, "Fatal RPython error\n");
            abort();
        }'''))]
        self.ecis = []
        self.entrypoints = set()

    def transform_graph(self, graph):
        if (graph not in self.transformed_graphs and
            hasattr(graph.returnblock.inputargs[0], 'concretetype')):
            self.transformed_graphs.add(graph)
            self.exctransformer.create_exception_handling(graph)
            self.gcpolicy.transform_graph(graph)

    def prepare(self, entrypoint, secondary_entrypoints):
        if callable(entrypoint):
            bk = self.translator.annotator.bookkeeper
            has_tls = bool(bk.thread_local_fields)
            setup_ptr = self.gcpolicy.get_setup_ptr()
            def main(argc, argv):
                llop.gc_stack_bottom(lltype.Void)
                try:
                    if has_tls:
                        rpy_tls_program_init()
                    if setup_ptr is not None:
                        setup_ptr()
                    args = [rffi.charp2str(argv[i]) for i in range(argc)]
                    return entrypoint(args)
                except Exception, exc:
                    write(2, 'DEBUG: An uncaught exception was raised in '
                             'entrypoint: ' + str(exc) + '\n')
                    return 1
            main.c_name = 'main'

            mixlevelannotator = MixLevelHelperAnnotator(self.translator.rtyper)
            arg1 = lltype_to_annotation(rffi.INT)
            arg2 = lltype_to_annotation(rffi.CCHARPP)
            res = lltype_to_annotation(lltype.Signed)
            graph = mixlevelannotator.getgraph(main, [arg1, arg2], res)
            mixlevelannotator.finish()
            mixlevelannotator.backend_optimize()
            self.entrypoints.add(getfunctionptr(graph)._obj)
        # rpython_startup_code doesn't work with GenLLVM yet
        # needs upstream refactoring
        self.entrypoints.update(
                ep._obj for ep in secondary_entrypoints
                if getattr(getattr(ep._obj, '_callable', None), 'c_name', None)
                   != 'rpython_startup_code')

        for graph in self.translator.graphs:
            self.transform_graph(graph)
        self.ovf_err = self.exctransformer.get_builtin_exception(OverflowError)
        ovf_err_inst = self.ovf_err[1]
        self.gcpolicy._consider_constant(ovf_err_inst._T, ovf_err_inst._obj)

        # XXX for some reason, this is needed to make all tests pass
        tmp = self.exctransformer.get_builtin_exception(OSError)[1]
        self.gcpolicy._consider_constant(tmp._T, tmp._obj)

        self.gcpolicy.finish()

    def _get_target_information(self):
        """
        Get datalayout, triple, and "target-cpu" and "target-features"
        attributes for a generic version of the CPU we are compiling on.

        This passes a small C code snippet to clang and parses the output in a
        way that could easily break with any future LLVM version.
        """
        output = cmdexec(
                'echo "void test() {{}}" | clang -x c - -emit-llvm -S -o -'
                .format(devnull))
        for line in output.splitlines(True):
            if line.startswith('target '):
                yield line
            if line.startswith('attributes'):
                assert line.startswith('attributes #0 = { ')
                assert line.endswith(' }\n')
                attributes_str = line[len('attributes #0 = { '):-len(' }\n')]
                for attribute in attributes_str.split():
                    if attribute.startswith('"target-cpu"='):
                        target_cpu_attribute = attribute
                    if attribute.startswith('"target-features"='):
                        target_features_attribute = attribute
                database.target_attributes = '{} {}'.format(
                        target_cpu_attribute, target_features_attribute)

    def _write_special_declarations(self, f):
        compiler_info_str = "LLVM " + cmdexec('llvm-config --version').strip()
        cstr_type = '[{} x i8]'.format(len(compiler_info_str) + 1)
        f.write('@compiler_info = private unnamed_addr constant {} c"{}\\00"\n'
                .format(cstr_type, compiler_info_str))
        database.compiler_info = ('bitcast({}* @compiler_info to [0 x i8]*)'
                .format(cstr_type))

        f.write('declare void @abort() noreturn nounwind\n')
        f.write('declare void @llvm.gcroot(i8** %ptrloc, i8* %metadata)\n')
        f.write('@__gcmap = external constant i8\n')
        for op in ('sadd', 'ssub', 'smul'):
            f.write('declare {{{T}, i1}} @llvm.{op}.with.overflow.{T}('
                    '{T} %a, {T} %b)\n'.format(op=op, T=SIGNED_TYPE))
        exctrans = self.exctransformer
        f.write('define internal void @_raise_ovf(i1 %x) alwaysinline {{\n'
                '  block0:\n'
                '    br i1 %x, label %block1, label %block2\n'
                '  block1:\n'
                '    call void {raise_.V}({type.TV}, {inst.TV})\n'
                '    ret void\n'
                '  block2:\n'
                '    ret void\n'
                '}}\n'.format(raise_=get_repr(exctrans.rpyexc_raise_ptr),
                              type=get_repr(self.ovf_err[0]),
                              inst=get_repr(self.ovf_err[1])))
        f.write('!0 = !{ }\n')

    def gen_source(self):
        global database

        self.work_dir = udir.join(uniquemodulename('llvm'))
        self.work_dir.mkdir()
        self.main_ll_file = self.work_dir.join('main.ll')
        with self.main_ll_file.open('w') as f:
            database = Database(self, f)

            for line in self._get_target_information():
                f.write(line)

            from rpython.translator.c.database import LowLevelDatabase
            from rpython.translator.c.genc import gen_threadlocal_structdef
            db = LowLevelDatabase(self.translator)
            with self.work_dir.join('structdef.h').open('w') as f2:
                tls_fields = gen_threadlocal_structdef(f2, db)
            database.tls_struct = StructType()
            database.tls_struct.setup(
                    'tls', [(LLVMInt, 'ready'), (LLVMAddress, 'stack_end')] +
                           [(database.get_type(fld.FIELDTYPE), fld.fieldname)
                            for fld in tls_fields], False)

            self._write_special_declarations(f)
            for export in self.entrypoints:
                get_repr(export._as_ptr()).V

            if database.stack_bottoms:
                items = ('i8* bitcast({} to i8*)'
                        .format(ref) for ref in database.stack_bottoms)
                f.write('@gc_stack_bottoms = global [{} x i8*] [ {} ], '
                        'section "llvm.metadata"\n'
                        .format(len(database.stack_bottoms), ', '.join(items)))

        exports.clear()

    def _execute(self, args):
        cmdexec(' '.join(map(str, args)))

    def _compile(self, shared=False):
        # parse RPYTHON_LLVM_ASSEMBLY environment variable
        llvm_assembly = environ.get('RPYTHON_LLVM_ASSEMBLY', 'false')
        if llvm_assembly == 'true':
            llvm_assembly = True
        elif llvm_assembly == 'false':
            llvm_assembly = False
        else:
            raise Exception("RPYTHON_LLVM_ASSEMBLY must be 'false' or 'true'.")

        # merge ECIs
        c_dir = local(cdir)
        eci = ExternalCompilationInfo(
            include_dirs=[cdir, c_dir / '..' / 'llvm', self.work_dir],
            includes=['stdio.h', 'stdlib.h', 'src/threadlocal.h',
                      'src/stack.h', 'structdef.h'],
            separate_module_files=[c_dir / 'src' / 'threadlocal.c',
                                   c_dir / 'src' / 'stack.c'],
            separate_module_sources=['\n'.join(self.sources)],
            post_include_bits=['typedef _Bool bool_t;']
        ).merge(*self.ecis).convert_sources_to_files()

        # compile c files to LLVM IR
        ll_files = [self.main_ll_file]
        c_modules_dir = self.work_dir.join('c_modules')
        c_modules_dir.mkdir()
        c_args = ['clang', '-O3', '-emit-llvm', '-S']
        c_args.extend('-I{}'.format(ic) for ic in eci.include_dirs)
        for c_file in eci.separate_module_files:
            ll_file = local(c_file).new(dirname=c_modules_dir, ext='.ll')
            ll_files.append(ll_file)
            self._execute(c_args + [c_file, '-o', ll_file])

        # link LLVM IR into one module
        linked_file = self.work_dir.join('output_unoptimized.' +
                                         ('ll' if llvm_assembly else 'bc'))
        link_ir_args = ['llvm-link'] + ll_files + ['-o', linked_file]
        self._execute(link_ir_args + (['-S'] if llvm_assembly else []))

        # optimize this module
        optimized_file = self.work_dir.join('output_optimized.' +
                                            ('ll' if llvm_assembly else 'bc'))
        opt_args = ['opt', '-load',
                    self._compile_llvm_plugin('InternalizeHiddenSymbols.cpp'),
                    '-O3', linked_file, '-o', optimized_file]
        self._execute(opt_args + (['-S'] if llvm_assembly else []))

        # compile object file
        llc_args = ['llc', '-O3']
        if self.translator.config.translation.gcrootfinder == 'llvmgcroot':
            llc_args.append('-load')
            llc_args.append(self._compile_llvmgcroot())
        if shared:
            llc_args.append('-relocation-model=pic')
        if llvm_assembly:
            object_file = self.work_dir.join('output.s')
        else:
            object_file = self.work_dir.join(
                    'output.' + self.translator.platform.o_ext)
            llc_args.append('-filetype=obj')
        self._execute(llc_args + [optimized_file, '-o', object_file])

        # link executable
        link_args = ['clang', '-O3', '-pthread']
        link_args.extend('-L{}'.format(ld) for ld in eci.library_dirs)
        link_args.extend('-l{}'.format(li) for li in eci.libraries)
        link_args.extend('{}'.format(lf) for lf in eci.link_files)
        if shared:
            link_args.append('-shared')
            output_file = object_file.new(ext=self.translator.platform.so_ext)
        else:
            output_file = object_file.new(ext=self.translator.platform.exe_ext)
        self._execute(link_args + [object_file, '-o', output_file])
        return output_file

    def _compile_llvm_plugin(self, relative_filename):
        this_file = local(__file__)
        plugin_cpp = this_file.new(basename=relative_filename)
        plugin_so = plugin_cpp.new(ext=self.translator.platform.so_ext)
        cflags = cmdexec('llvm-config --cxxflags').strip() + ' -fno-rtti'
        cmdexec('clang {} -shared {} -o {}'.format(cflags, plugin_cpp,
                                                   plugin_so))
        return plugin_so

    def compile(self, exe_name):
        return self._compile()
