from itertools import count

from py.process import cmdexec
from pypy.objspace.flow.model import mkentrymap, Constant, Variable
from pypy.rlib.jit import _we_are_jitted
from pypy.rlib.objectmodel import (Symbolic, ComputedIntSymbolic,
     CDefinedIntSymbolic, malloc_zero_filled, running_on_llinterp)
from pypy.rpython.lltypesystem import llarena, llgroup, llmemory, lltype, rffi
from pypy.rpython.memory.gctransform.framework import FrameworkGCTransformer
from pypy.rpython.memory.gctransform.transform import GCTransformer
from pypy.rpython.tool import rffi_platform
from pypy.rpython.typesystem import getfunctionptr
from pypy.translator.gensupp import uniquemodulename
from pypy.translator.unsimplify import remove_double_links
from pypy.tool.udir import udir


class Type(object):
    varsize = False

    def repr_type(self, extra_len=None):
        return self.typestr

    def is_zero(self, value):
        raise NotImplementedError("Override in subclass.")

    def get_extra_len(self, value):
        raise NotImplementedError("Override in subclass.")

    def repr_value(self, obj):
        raise NotImplementedError("Override in subclass.")

    def repr_type_and_value(self, value):
        if self.varsize:
            self.repr_type(None)
            extra_len = self.get_extra_len(value)
            return '{} {}'.format(self.repr_type(extra_len),
                                  self.repr_value(value, extra_len))
        return '{} {}'.format(self.repr_type(), self.repr_value(value))

    def repr_ref(self, ptr_type, obj):
        name = database.unique_name('@global')
        if self.varsize:
            extra_len = self.get_extra_len(obj)
            ptr_type.refs[obj] = 'bitcast({}* {} to {}*)'.format(
                    self.repr_type(extra_len), name, self.repr_type(None))
        else:
            ptr_type.refs[obj] = name
        database.f.write('{} = global {}\n'.format(
                name, self.repr_type_and_value(obj)))


class VoidType(Type):
    typestr = 'void'

    def is_zero(self, value):
        return True

    def repr_value(self, value, extra_len=None):
        if value is None:
            return 'null'
        raise TypeError


class IntegralType(Type):
    def __init__(self, bytewidth, unsigned):
        self.bitwidth = bytewidth * 8
        self.unsigned = unsigned
        self.typestr = 'i{}'.format(self.bitwidth)

    def is_zero(self, value):
        if isinstance(value, Symbolic):
            return False
        return value == 0

    def repr_value(self, value, extra_len=None):
        if isinstance(value, (int, long)):
            return str(value)
        elif isinstance(value, ComputedIntSymbolic):
            return str(value.compute_fn())
        elif isinstance(value, llarena.RoundedUpForAllocation):
            size = ('select(i1 icmp sgt({minsize.TV}, {basesize.TV}), '
                    '{minsize.TV}, {basesize.TV})'
                            .format(minsize=get_repr(value.minsize),
                                    basesize=get_repr(value.basesize)))
            return 'and(i64 add(i64 {}, i64 {}), i64 {})'.format(
                    size, align-1, ~(align-1))
        elif isinstance(value, llmemory.GCHeaderOffset):
            return '0'
        elif isinstance(value, llmemory.CompositeOffset):
            assert len(value.offsets) == 2
            offset1, offset2 = value.offsets
            return 'add(i64 {}, i64 {})'.format(self.repr_value(offset1),
                                                self.repr_value(offset2))
        elif isinstance(value, llmemory.AddressOffset):
            indices = []
            to = self.add_offset_indices(indices, value)
            if to is lltype.Void:
                return '0'
            return 'ptrtoint({}* getelementptr({}* null, {}) to i64)'.format(
                    database.get_type(to).repr_type(),
                    database.get_type(value.TYPE).repr_type(),
                    ', '.join(indices))
        elif isinstance(value, llgroup.GroupMemberOffset):
            grpptr = get_repr(value.grpptr)
            member = get_repr(value.member)
            return ('ptrtoint({member.T} getelementptr({grpptr.T} null, '
                    'i64 0, i32 {value.index}) to i32)').format(**locals())
        elif isinstance(value, llgroup.CombinedSymbolic):
            lp = get_repr(value.lowpart)
            rest = get_repr(value.rest)
            return 'or(i64 sext({lp.TV} to i64), {rest.TV})'.format(**locals())
        elif isinstance(value, CDefinedIntSymbolic):
            if value is malloc_zero_filled:
                return '1'
            elif value is _we_are_jitted:
                return '0'
            elif value is running_on_llinterp:
                return '0'
        raise NotImplementedError(value)

    def add_offset_indices(self, indices, offset):
        if isinstance(offset, llmemory.ItemOffset):
            indices.append('i64 {}'.format(offset.repeat))
            return offset.TYPE
        if not indices:
            indices.append('i64 0')
        if isinstance(offset, llmemory.FieldOffset):
            indices.append('i32 {}'.format(
                    offset.TYPE._names_without_voids().index(offset.fldname)))
            return offset.TYPE._flds[offset.fldname]
        if isinstance(offset, llmemory.ArrayLengthOffset):
            indices.append('i32 0')
            return lltype.Signed
        if isinstance(offset, llmemory.ArrayItemsOffset):
            if not offset.TYPE._hints.get("nolength", False):
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
        elif isinstance(to, BasePtrType):
            return 'inttoptr'
        return 'bitcast'


class CharType(IntegralType):
    def __init__(self):
        self.bitwidth = 8
        self.unsigned = True
        self.typestr = 'i8'

    def is_zero(self, value):
        return value is None or value == '\00'

    def repr_value(self, value, extra_len=None):
        return str(ord(value))


class BoolType(IntegralType):
    def __init__(self):
        self.bitwidth = 1
        self.unsigned = True
        self.typestr = 'i1'

    def is_zero(self, value):
        return not value

    def repr_value(self, value, extra_len=None):
        if value:
            return 'true'
        return 'false'


class FloatType(Type):
    def __init__(self, typestr):
        self.typestr = typestr

    def is_zero(self, value):
        return float(value) == 0.0

    def repr_value(self, value, extra_len=None):
        return repr(float(value))


class BasePtrType(Type):
    def get_cast_op(self, to):
        if isinstance(to, IntegralType):
            return 'ptrtoint'
        return 'bitcast'


class AddressType(BasePtrType):
    typestr = 'i8*'

    def is_zero(self, value):
        return value.ptr is None

    def repr_value(self, value, extra_len=None):
        if value.ptr is None:
            return 'null'
        return "bitcast({ptr.TV} to i8*)".format(ptr=get_repr(value.ptr))


LLVMVoid = VoidType()
LLVMSigned = IntegralType(8, False)
LLVMUnsigned = IntegralType(8, True)
LLVMChar = CharType()
LLVMBool = BoolType()
LLVMFloat = FloatType('double')
LLVMSingleFloat = FloatType('float')
LLVMLongFloat = FloatType('x86_fp80')
LLVMAddress = AddressType()

PRIMITIVES = {
    lltype.Void: LLVMVoid,
    lltype.Signed: LLVMSigned,
    lltype.Unsigned: LLVMUnsigned,
    lltype.Char: LLVMChar,
    lltype.Bool: LLVMBool,
    lltype.Float: LLVMFloat,
    lltype.SingleFloat: LLVMSingleFloat,
    lltype.LongFloat: LLVMLongFloat,
    llmemory.Address: LLVMAddress
}
for type_ in rffi.NUMBER_TYPES:
    if type_ not in PRIMITIVES:
        PRIMITIVES[type_] = IntegralType(*rffi.size_and_sign(type_))


class PtrType(BasePtrType):
    @classmethod
    def to(cls, to):
        self = cls()
        self.to = to
        self.refs = {None: 'null'}
        return self

    def setup_from_lltype(self, db, type_):
        self.to = db.get_type(type_.TO)
        self.refs = {None: 'null'}

    def repr_type(self, extra_len=None):
        return self.to.repr_type() + '*'

    def is_zero(self, value):
        return not value

    def repr_value(self, value, extra_len=None):
        try:
            obj = value._obj
        except lltype.DelayedPointer:
            assert isinstance(value._obj0, str)
            database.delayed_ptrs.append(value)
            return '@rpy_' + value._obj0[len('delayed!'):]
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
                self.refs[obj] = 'bitcast({}* getelementptr({}, {}) to {})'\
                        .format(to.repr_type(), parent_ref,
                                ', '.join(gep.indices), self.repr_type())
            else:
                self.to.repr_ref(self, obj)
            return self.refs[obj]


class StructType(Type):
    def setup(self, name, fields):
        self.name = name
        self.fields = fields
        self.fldnames_without_voids = zip(*fields)[1]
        self.varsize = fields[-1][0].varsize
        self.size_variants = {}

    def setup_from_lltype(self, db, type_):
        self.name = '%struct.' + type_._name
        self.fields = [(db.get_type(type_._flds[f]), f) for f in type_._names]
        self.fldnames_without_voids = type_._names_without_voids()
        self.varsize = self.fields[-1][0].varsize
        self.size_variants = {}

    def repr_type(self, extra_len=None):
        if extra_len not in self.size_variants:
            if extra_len is not None:
                name = self.name + '_plus_{}'.format(extra_len)
            elif self.varsize:
                name = self.name + '_varsize'
            else:
                name = self.name
            self.size_variants[extra_len] = name = database.unique_name(name)
            lastname = self.fldnames_without_voids[-1]
            tmp = ('    {semicolon}{fldtype}{comma} ; {fldname}\n'.format(
                           semicolon=';' if fldtype is LLVMVoid else '',
                           fldtype=fldtype.repr_type(extra_len),
                           comma=',' if fldname is not lastname else '',
                           fldname=fldname)
                   for fldtype, fldname in self.fields)
            database.f.write('{} = type {{\n{}}}\n'.format(name, ''.join(tmp)))
        return self.size_variants[extra_len]

    def is_zero(self, value):
        return all(ft.is_zero(getattr(value, fn)) for ft, fn in self.fields)

    def get_extra_len(self, value):
        last_fldtype, last_fldname = self.fields[-1]
        return last_fldtype.get_extra_len(getattr(value, last_fldname))

    def repr_value(self, value, extra_len=None):
        if self.is_zero(value):
            return 'zeroinitializer'
        lastname = self.fldnames_without_voids[-1]
        tmp = ('    {semicolon}{fldtype} {fldvalue}{comma} ; {fldname}'.format(
                       semicolon=';' if fldtype is LLVMVoid else '',
                       fldtype=fldtype.repr_type(extra_len),
                       fldvalue=fldtype.repr_value(getattr(value, fldname),
                               extra_len).replace('\n', '\n    '),
                       comma=',' if fldname is not lastname else '',
                       fldname=fldname)
               for fldtype, fldname in self.fields)
        return '{{\n{}\n}}'.format('\n'.join(tmp))

    def add_indices(self, gep, attr):
        index = self.fldnames_without_voids.index(attr.value)
        gep.add_field_index(index)
        return self.fields[index][0]


class UnionHelper(object):
    def __init__(self, storage):
        self.storage = storage

class UnionType(Type):
    varsize = False

    def setup_from_lltype(self, db, type_):
        self.fields = [(db.get_type(type_._flds[f]), f) for f in type_._names]
        self.storage = max(self.fields, key=lambda x: x[0].bitwidth)[0]
        self.struct_type = StructType()
        self.struct_type.setup('%union', [(self.storage, 'storage')])

    def repr_type(self, extra_len=None):
        return self.struct_type.repr_type(extra_len)

    def is_zero(self, value):
        return all(ft.is_zero(getattr(value, fn)) for ft, fn in self.fields)

    def get_extra_len(self, value):
        raise TypeError

    def repr_value(self, value, extra_len=None):
        if self.is_zero(value):
            return 'zeroinitializer'
        raise TypeError

    def add_indices(self, gep, attr):
        gep.add_field_index(0)
        for fldtype, fldname in self.fields:
            if fldname == attr.value:
                gep.cast(self.storage, fldtype)
                return fldtype
        else:
            raise TypeError


class BareArrayType(Type):
    def setup(self, of, length):
        self.of = of
        self.length = length

    def setup_from_lltype(self, db, type_):
        self.setup(db.get_type(type_.OF), getattr(type_, 'length', None))

    def repr_type(self, extra_len=None):
        if self.of is LLVMVoid:
            return '[0 x {}]'
        if extra_len is not None:
            return '[{} x {}]'.format(extra_len, self.of.repr_type())
        elif self.length is None:
            return '[0 x {}]'.format(self.of.repr_type())
        return '[{} x {}]'.format(self.length, self.of.repr_type())

    @property
    def varsize(self):
        return self.length is None

    def is_zero(self, value):
        return all(self.of.is_zero(item) for item in value.items)

    def get_extra_len(self, value):
        try:
            return value.getlength()
        except AttributeError:
            assert isinstance(self.of, CharType)
            for i in count():
                if value.getitem(i) == '\00':
                    return i + 1

    def repr_value(self, value, extra_len=None):
        if self.is_zero(value):
            return 'zeroinitializer'
        if isinstance(self.of, CharType):
            return 'c"{}"'.format(''.join(i if 32 <= ord(i) <= 126 and i != '"'
                                          else r'\{:02x}'.format(ord(i))
                                  for i in value.items))
        return '[\n    {}\n]'.format(', '.join(self.of.repr_type_and_value(item)
                                               for item in value.items))

    def add_indices(self, gep, key):
        if key.type_ is LLVMVoid:
            index = int(key.value[4:])
        else:
            index = key.V
        gep.add_array_index(index)
        return self.of


class ArrayHelper(object):
    def __init__(self, value):
        self.len = value.getlength()
        self.items = value

class ArrayType(Type):
    varsize = True

    def setup_from_lltype(self, db, type_):
        of = db.get_type(type_.OF)
        tmp = '%array_of_' + of.repr_type().lstrip('%').replace('*', '_ptr')\
                                                       .replace('[', '_')\
                                                       .replace(']', '_')\
                                                       .replace('(', '_')\
                                                       .replace(')', '_')\
                                                       .replace(' ', '_')
        self.bare_array_type = BareArrayType()
        self.bare_array_type.setup(of, None)
        self.struct_type = StructType()
        self.struct_type.setup(
                tmp, [(LLVMSigned, 'len'), (self.bare_array_type, 'items')])

    def repr_type(self, extra_len=None):
        return self.struct_type.repr_type(extra_len)

    def is_zero(self, value):
        return self.struct_type.is_zero(ArrayHelper(value))

    def get_extra_len(self, value):
        return self.struct_type.get_extra_len(ArrayHelper(value))

    def repr_value(self, value, extra_len=None):
        return self.struct_type.repr_value(ArrayHelper(value), extra_len)

    def repr_type_and_value(self, value):
        return self.struct_type.repr_type_and_value(ArrayHelper(value))

    def add_indices(self, gep, index):
        gep.add_field_index(1)
        return self.bare_array_type.add_indices(gep, index)


class Group(object):
    pass


class GroupType(Type):
    def setup_from_lltype(self, db, type_):
        self.typestr = '%group_' + type_.name

    def repr_ref(self, ptr_type, obj):
        groupname = ptr_type.refs[obj] = '@group_' + obj.name
        group = Group()
        fields = []
        for i, member in enumerate(obj.members):
            fldname = 'member{}'.format(i)
            fields.append((database.get_type(member._TYPE), fldname))
            setattr(group, fldname, member)
            member_ptr_refs = database.get_type(lltype.Ptr(member._TYPE)).refs
            member_ptr_refs[member] = 'getelementptr({}* {}, i64 0, i32 {})'\
                    .format(self.typestr, groupname, i)
        struct_type = StructType()
        struct_type.setup(self.typestr, fields)
        database.f.write('{} = global {}\n'.format(
                groupname, struct_type.repr_type_and_value(group)))


align = rffi_platform.memory_alignment()
ROUND_UP_FOR_ALLOCATION = ( # XXX make it a LLOp?
        'define i64 @ROUND_UP_FOR_ALLOCATION(i64 %basesize, i64 %minsize) {{\n'
        '    %cond = icmp sgt i64 %minsize, %basesize\n'
        '    %size = select i1 %cond, i64 %minsize, i64 %basesize\n'
        '    %tmp1 = add i64 %size, {}\n'
        '    %tmp2 = and i64 %tmp1, {}\n'
        '    ret i64 %tmp2\n'
        '}}\n').format(align-1, ~(align-1))

class FuncType(Type):
    def setup_from_lltype(self, db, type_):
        self.result = db.get_type(type_.RESULT)
        self.args = [db.get_type(argtype) for argtype in type_.ARGS]

    def repr_type(self, extra_len=None):
        return '{} ({})'.format(self.result.repr_type(),
                                ', '.join(arg.repr_type()
                                          for arg in self.args))

    def repr_ref(self, ptr_type, obj):
        if getattr(obj, 'external', None) == 'C':
            ptr_type.refs[obj] = name = '@' + obj._name
            if obj._name == 'ROUND_UP_FOR_ALLOCATION': # XXX
                database.f.write(ROUND_UP_FOR_ALLOCATION)
            elif obj._name not in ('malloc', 'free'):
                database.f.write('declare {} {}({})\n'.format(
                        self.result.typestr, name,
                        ', '.join(arg.repr_type() for arg in self.args)))
        else:
            name = database.unique_name('@rpy_' + obj._name
                    .replace(',', '_').replace(' ', '_')
                    .replace('(', '_').replace(')', '_')
                    .replace('<', '_').replace('>', '_'))
            ptr_type.refs[obj] = name
            database.genllvm.transform_graph(obj.graph)
            writer = FunctionWriter()
            writer.write_graph(name, obj.graph)
            database.f.writelines(writer.lines)


class OpaqueType(Type):
    typestr = 'i8*'

    def setup_from_lltype(self, db, type_):
        pass

    def is_zero(self, value):
        return True

    def repr_value(self, value, extra_len=None):
        return 'null'


class Database(object):
    def __init__(self, genllvm, f):
        self.genllvm = genllvm
        self.f = f
        self.names_counter = {}
        self.types = PRIMITIVES.copy()
        self.delayed_ptrs = []

    def get_type(self, type_):
        try:
            return self.types[type_]
        except KeyError:
            if isinstance(type_, lltype.Ptr):
                class_ = PtrType
            elif isinstance(type_, lltype.FixedSizeArray):
                class_ = BareArrayType
            elif isinstance(type_, lltype.Struct):
                if type_._hints.get("union", False):
                    class_ = UnionType
                else:
                    class_ = StructType
            elif isinstance(type_, lltype.Array):
                if type_._hints.get("nolength", False):
                    class_ = BareArrayType
                else:
                    class_ = ArrayType
            elif isinstance(type_, lltype.FuncType):
                class_ = FuncType
            elif isinstance(type_, lltype.OpaqueType):
                class_ = OpaqueType
            elif isinstance(type_, llgroup.GroupType):
                class_ = GroupType
            else:
                raise TypeError('type_ is {!r}'.format(type_))

            self.types[type_] = ret = class_()
            ret.setup_from_lltype(self, type_)
            return ret

    def unique_name(self, name):
        if name not in self.names_counter:
            self.names_counter[name] = 0
            return name
        else:
            ret = '{}_{}'.format(name, self.names_counter[name])
            self.names_counter[name] += 1
            return ret


OPS = {
        'int_add_ovf': 'add', # XXX check for overflow
        'int_mul_ovf': 'mul', # XXX check for overflow
}
for type_ in ['int', 'uint', 'llong', 'ullong']:
    OPS[type_ + '_lshift'] = 'shl'
    OPS[type_ + '_rshift'] = 'lshr' if type_[0] == 'u' else 'ashr'
    OPS[type_ + '_floordiv'] = 'udiv' if type_[0] == 'u' else 'sdiv'
    OPS[type_ + '_mod'] = 'urem' if type_[0] == 'u' else 'srem'
    for op in ['add', 'sub', 'mul', 'and', 'or', 'xor']:
        OPS['{}_{}'.format(type_, op)] = op

for type_ in ['float']:
    for op in ['add', 'sub', 'mul', 'div']:
        OPS['{}_{}'.format(type_, op)] = 'f' + op

for type_, prefix in [('char', 'u'), ('unichar', 'u'), ('int', 's'),
                      ('uint', 'u'), ('llong', 's'), ('ullong', 'u'),
                      ('adr', 's'), ('ptr', 's')]:
    OPS[type_ + '_eq'] = 'icmp eq'
    OPS[type_ + '_ne'] = 'icmp ne'
    for op in ['gt', 'ge', 'lt', 'le']:
        OPS['{}_{}'.format(type_, op)] = 'icmp {}{}'.format(prefix, op)

for type_ in ['float']:
    for op in ['eq', 'ne', 'gt', 'ge', 'lt', 'le']:
        OPS['{}_{}'.format(type_, op)] = 'fcmp o' + op

del type_
del op


class ConstantRepr(object):
    def __init__(self, type_, value):
        self.type_ = type_
        self.value = value

    @property
    def T(self):
        return self.type_.repr_type()

    @property
    def V(self):
        return self.type_.repr_value(self.value)

    @property
    def TV(self):
        return self.type_.repr_type_and_value(self.value)

    def __repr__(self):
        return '<{} {}>'.format(self.type_.repr_type(), self.value)


class VariableRepr(object):
    def __init__(self, type_, name):
        self.type_ = type_
        self.name = name

    @property
    def T(self):
        return self.type_.repr_type()

    @property
    def V(self):
        return self.name

    @property
    def TV(self):
        return '{} {}'.format(self.type_.repr_type(), self.name)

    def __repr__(self):
        return '<{} {}>'.format(self.type_.repr_type(), self.name)


def get_repr(cov):
    if isinstance(cov, Constant):
        return ConstantRepr(database.get_type(cov.concretetype), cov.value)
    elif isinstance(cov, Variable):
        return VariableRepr(database.get_type(cov.concretetype), '%'+cov.name)
    return ConstantRepr(database.get_type(lltype.typeOf(cov)), cov)


class GEP(object):
    def __init__(self, func_writer, ptr):
        self.func_writer = func_writer
        self.ptr = ptr
        self.indices = ['i64 0']

    def add_array_index(self, index):
        self.indices.append('i64 {}'.format(index))

    def add_field_index(self, index):
        self.indices.append('i32 {}'.format(index))

    def cast(self, fr, to):
        t1 = self.func_writer._tmp(PtrType.to(fr))
        t2 = self.func_writer._tmp(PtrType.to(to))
        self.assign(t1)
        self.func_writer.w('{t2.V} = bitcast {t1.TV} to {t2.T}'
                .format(**locals()))
        self.ptr = t2
        self.indices[:] = ['i64 0']

    def assign(self, result):
        self.func_writer.w('{result.V} = getelementptr {ptr.TV}, {gep}'.format(
                result=result, ptr=self.ptr, gep=', '.join(self.indices)))


class FunctionWriter(object):
    def __init__(self):
        self.lines = []
        self.tmp_counter = count()

    def w(self, line, indent='    '):
        self.lines.append('{}{}\n'.format(indent, line))

    def write_graph(self, name, graph):
        self.w('define {retvar.T} {name}({a}) {{'.format(
                       retvar=get_repr(graph.getreturnvar()),
                       name=name,
                       a=', '.join(get_repr(arg).TV for arg in graph.getargs()
                                   if arg.concretetype is not lltype.Void)),
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
        self.w('}', '')

    def write_phi_nodes(self, block):
        for i, arg in enumerate(block.inputargs):
            if arg.concretetype == lltype.Void:
                continue
            s = ', '.join('[{}, %{}]'.format(
                    get_repr(l.args[i]).V, self.block_to_name[l.prevblock])
                    for l in self.entrymap[block] if l.prevblock is not None)
            self.w('{arg.V} = phi {arg.T} {s}'.format(arg=get_repr(arg), s=s))

    def write_operations(self, block):
        for op in block.operations:
            self.w('; {}'.format(op))
            opname = op.opname
            opres = get_repr(op.result)
            opargs = map(get_repr, op.args)
            if opname in OPS:
                simple_op = OPS[opname]
                self.w('{opres.V} = {simple_op} {opargs[0].TV}, {opargs[1].V}'
                        .format(**locals()))
            elif opname.startswith('cast_') or opname.startswith('truncate_'):
                self._cast(get_repr(op.result), get_repr(op.args[0]))
            else:
                func = getattr(self, 'op_' + opname, None)
                if func is not None:
                    func(opres, *opargs)
                else:
                    raise NotImplementedError(op)

    def _tmp(self, type_=None):
        return VariableRepr(type_, '%tmp{}'.format(next(self.tmp_counter)))

    # XXX: implement

    def op_zero_gc_pointers_inside(self, result, var):
        pass

    def op_debug_print(self, result, *args):
        pass

    def op_debug_assert(self, result, *args):
        pass

    def op_debug_llinterpcall(self, result, *args):
        if result.type_ is not LLVMVoid:
            self.w('{result.V} = bitcast {result.T} undef to {result.T}'
                    .format(**locals()))

    def op_debug_fatalerror(self, result, *args):
        pass

    def op_debug_record_traceback(self, result, *args):
        pass

    def op_debug_start_traceback(self, result, *args):
        pass

    def op_debug_catch_exception(self, result, *args):
        pass

    def op_debug_reraise_traceback(self, result, *args):
        pass

    def op_debug_start(self, result, *args):
        pass

    def op_debug_stop(self, result, *args):
        pass

    def op_debug_nonnull_pointer(self, result, *args):
        pass

    def op_track_alloc_start(self, result, *args):
        pass

    def op_track_alloc_stop(self, result, *args):
        pass

    def _cast(self, to, fr):
        if fr.type_ is LLVMVoid:
            return
        elif fr.type_ is to.type_:
            op = 'bitcast'
        else:
            op = fr.type_.get_cast_op(to.type_)
        self.w('{to.V} = {op} {fr.TV} to {to.T}'.format(**locals()))
    op_same_as = _cast
    op_force_cast = _cast
    op_raw_malloc_usage = _cast

    def op_direct_call(self, result, fn, *args):
        args = ', '.join('{arg.TV}'.format(arg=arg) for arg in args
                         if arg.type_ is not LLVMVoid)
        if result.type_ is LLVMVoid:
            fmt = 'call void {fn.V}({args})'
        elif (isinstance(result.type_, PtrType) and
              isinstance(result.type_.to, FuncType)):
            fmt = '{result.V} = call {fn.TV}({args})'
        else:
            fmt = '{result.V} = call {result.T} {fn.V}({args})'
        self.w(fmt.format(**locals()))
    op_indirect_call = op_direct_call

    def _get_element_ptr(self, ptr, fields, result):
        gep = GEP(self, ptr)
        type_ = ptr.type_.to
        for field in fields:
            type_ = type_.add_indices(gep, field)
        gep.assign(result)

    def _get_element_ptr_op(self, result, ptr, *fields):
        self._get_element_ptr(ptr, fields, result)
    op_getsubstruct = op_getarraysubstruct = _get_element_ptr_op

    def _get_element(self, result, var, *fields):
        if result.type_ is not LLVMVoid:
            t = self._tmp()
            self._get_element_ptr(var, fields, t)
            self.w('{result.V} = load {result.T}* {t.V}'.format(**locals()))
    op_getfield = op_bare_getfield = _get_element
    op_getinteriorfield = op_bare_getinteriorfield = _get_element
    op_getarrayitem = op_bare_getarrayitem = _get_element

    def _set_element(self, result, var, *rest):
        fields = rest[:-1]
        value = rest[-1]
        t = self._tmp()
        self._get_element_ptr(var, fields, t)
        self.w('store {value.TV}, {value.T}* {t.V}'.format(**locals()))
    op_setfield = op_bare_setfield = _set_element
    op_setinteriorfield = op_bare_setinteriorfield = _set_element
    op_setarrayitem = op_bare_setarrayitem = _set_element

    def op_direct_fieldptr(self, result, ptr, field):
        t = self._tmp(PtrType.to(result.type_.to.of))
        self._get_element_ptr(ptr, [field], t)
        self.w('{result.V} = bitcast {t.TV} to {result.T}'.format(**locals()))

    def op_direct_arrayitems(self, result, ptr):
        t = self._tmp(PtrType.to(result.type_.to.of))
        self._get_element_ptr(ptr, [ConstantRepr(LLVMSigned, 0)], t)
        self.w('{result.V} = bitcast {t.TV} to {result.T}'.format(**locals()))

    def op_direct_ptradd(self, result, var, val):
        self.w('{result.V} = getelementptr {var.TV}, {val.TV}'
                .format(**locals()))

    def op_getarraysize(self, result, ptr, *fields):
        gep = GEP(self, ptr)
        type_ = ptr.type_.to
        for field in fields:
            type_ = type_.add_indices(gep, field)

        if isinstance(type_, BareArrayType):
            self.w('{result.V} = add i64 0, {type_.length}'.format(**locals()))
        else:
            gep.add_field_index(0)
            t = self._tmp()
            gep.assign(t)
            self.w('{result.V} = load i64* {t.V}'.format(**locals()))
    op_getinteriorarraysize = op_getarraysize

    def op_int_is_true(self, result, var):
        self.w('{result.V} = icmp ne i64 {var.V}, 0'.format(**locals()))
    op_uint_is_true = op_int_is_true

    def op_int_neg(self, result, var):
        self.w('{result.V} = sub {var.T} 0, {var.V}'.format(**locals()))

    def op_int_invert(self, result, var):
        self.w('{result.V} = xor {var.TV}, -1'.format(**locals()))

    def op_int_add_nonneg_ovf(self, result, val1, val2):
        self.w('{result.V} = add {val1.TV}, {val2.V}'.format(**locals()))

    def op_ptr_iszero(self, result, var):
        self.w('{result.V} = icmp eq {var.TV}, null'.format(**locals()))

    def op_ptr_nonzero(self, result, var):
        self.w('{result.V} = icmp ne {var.TV}, null'.format(**locals()))

    def op_adr_delta(self, result, arg1, arg2):
        t1 = self._tmp()
        t2 = self._tmp()
        self.w('{t1.V} = ptrtoint {arg1.TV} to i64'.format(**locals()))
        self.w('{t2.V} = ptrtoint {arg2.TV} to i64'.format(**locals()))
        self.w('{result.V} = sub i64 {t1.V}, {t2.V}'.format(**locals()))

    def _adr_op(int_op):
        def f(self, result, arg1, arg2):
            t1 = self._tmp()
            t2 = self._tmp()
            self.w('{t1.V} = ptrtoint {arg1.TV} to i64'.format(**locals()))
            int_op # reference to include it in locals()
            self.w('{t2.V} = {int_op} i64 {t1.V}, {arg2.V}'.format(**locals()))
            self.w('{result.V} = inttoptr i64 {t2.V} to {result.T}'
                    .format(**locals()))
        return f
    op_adr_add = _adr_op('add')
    op_adr_sub = _adr_op('sub')

    def op_raw_malloc(self, result, size):
        self.w('{result.V} = call i8* @malloc({size.TV})'.format(**locals()))

    def op_raw_free(self, result, ptr):
        self.w('call void @free({ptr.TV})'.format(**locals()))

    def _get_addr(self, ptr_to, addr, incr):
        t1 = self._tmp(PtrType.to(ptr_to))
        t2 = self._tmp(PtrType.to(ptr_to))
        self.w('{t1.V} = bitcast {addr.TV} to {t1.T}'.format(**locals()))
        self.w('{t2.V} = getelementptr {t1.TV}, {incr.TV}'.format(**locals()))
        return t2

    def op_raw_load(self, result, addr, _, incr):
        addr = self._get_addr(result.type_, addr, incr)
        self.w('{result.V} = load {addr.TV}'.format(**locals()))

    def op_raw_store(self, result, addr, _, incr, value):
        addr = self._get_addr(value.type_, addr, incr)
        self.w('store {value.TV}, {addr.TV}'.format(**locals()))

    def op_raw_memclear(self, result, ptr, size):
        self.w('call void @llvm.memset.p0i8.i64 ('
               '{ptr.TV}, i8 0, {size.TV}, i32 0, i1 0)'.format(**locals()))

    def op_raw_memcopy(self, result, src, dst, size):
        self.w('call void @llvm.memcpy.p0i8.p0i8.i64 ({dst.TV}, {src.TV}, '
               '{size.TV}, i32 0, i1 0)'.format(**locals()))

    def op_extract_ushort(self, result, val):
        self.w('{result.V} = trunc {val.TV} to {result.T}'.format(**locals()))

    def op_combine_ushort(self, result, ushort, rest):
        t = self._tmp(result.type_)
        self.w('{t.V} = zext {ushort.TV} to {t.T}'.format(**locals()))
        self.w('{result.V} = or {t.TV}, {rest.V}'.format(**locals()))

    def op_get_group_member(self, result, groupptr, compactoffset):
        t1 = self._tmp()
        t2 = self._tmp()
        self.w('{t1.V} = zext {compactoffset.TV} to i64'.format(**locals()))
        self.w('{t2.V} = add i64 ptrtoint({groupptr.TV} to i64), {t1.V}'
                .format(**locals()))
        self.w('{result.V} = inttoptr i64 {t2.V} to {result.T}'
                .format(**locals()))

    def op_get_next_group_member(self, result, groupptr, compactoffset,
                                 skipoffset):
        t1 = self._tmp()
        t2 = self._tmp()
        t3 = self._tmp()
        self.w('{t1.V} = zext {compactoffset.TV} to i64'.format(**locals()))
        self.w('{t2.V} = add i64 ptrtoint({groupptr.TV} to i64), {t1.V}'
                .format(**locals()))
        self.w('{t3.V} = add i64 {t2.V}, {skipoffset.V}'.format(**locals()))
        self.w('{result.V} = inttoptr i64 {t3.V} to {result.T}'
                .format(**locals()))

    def op_gc_gettypeptr_group(self, result, v_obj, grpptr, skipoffset, vtableinfo):
        # XXX
        self.w('{result.V} = inttoptr i64 0 to {result.T}'.format(**locals()))

    def op_gc_reload_possibly_moved(self, result, v_newaddr, v_targetvar):
        pass

    def op_keepalive(self, result, var):
        pass

    def write_branches(self, block):
        if len(block.exits) == 0:
            self.write_returnblock(block)
        elif len(block.exits) == 1:
            self.w('br label %' + self.block_to_name[block.exits[0].target])
        elif len(block.exits) == 2:
            assert block.exitswitch.concretetype is lltype.Bool
            for link in block.exits:
                if link.llexitcase:
                    true = self.block_to_name[link.target]
                else:
                    false = self.block_to_name[link.target]
            self.w('br i1 {}, label %{}, label %{}'.format(
                    get_repr(block.exitswitch).V, true, false))
        else:
            raise NotImplementedError

    def write_returnblock(self, block):
        ret = block.inputargs[0]
        if ret.concretetype is lltype.Void:
            self.w('ret void')
        else:
            self.w('ret {ret.TV}'.format(ret=get_repr(ret)))


class GCPolicy(object):
    def __init__(self, genllvm):
        self.genllvm = genllvm

    def transform_graph(self, graph):
        raise NotImplementedError("Override in subclass.")

    def finish(self):
        while database.delayed_ptrs:
            self.gctransformer.finish_helpers()

            delayed_ptrs = database.delayed_ptrs
            database.delayed_ptrs = []
            for ptr in delayed_ptrs:
                database.genllvm.transform_graph(ptr._obj.graph)
                get_repr(ptr).V

            finish_tables = self.gctransformer.get_finish_tables()
            if hasattr(finish_tables, '__iter__'):
                list(finish_tables)


class RawGCTransformer(GCTransformer):
    def gct_fv_gc_malloc(self, hop, flags, *args, **kwds):
        flags['zero'] = True
        return self.gct_fv_raw_malloc(hop, flags, *args, **kwds)

    def gct_fv_gc_malloc_varsize(self, hop, flags, *args, **kwds):
        #flags['zero'] = True
        return self.gct_fv_raw_malloc_varsize(hop, flags, *args, **kwds)


class RawGCPolicy(GCPolicy):
    def __init__(self, genllvm):
        self.genllvm = genllvm
        self.gctransformer = RawGCTransformer(genllvm.translator)


class FrameworkGCPolicy(GCPolicy):
    def __init__(self, genllvm):
        self.genllvm = genllvm
        self.gctransformer = FrameworkGCTransformer(genllvm.translator)


class GenLLVM(object):
    def __init__(self, translator, standalone):
        self.translator = translator
        self.exctransformer = translator.getexceptiontransformer()
        self.gcpolicy = {
            'none': RawGCPolicy,
            'framework': FrameworkGCPolicy
        }[translator.config.translation.gctransformer](self)
        self.transformed_graphs = set()

    def transform_graph(self, graph):
        if (graph not in self.transformed_graphs and
            hasattr(graph.returnblock.inputargs[0], 'concretetype')):
            self.transformed_graphs.add(graph)
            self.exctransformer.create_exception_handling(graph)
            self.gcpolicy.gctransformer.transform_graph(graph)
            remove_double_links(self.translator.annotator, graph)

    def gen_source(self, entry_point):
        global database

        self.entry_point = entry_point
        self.base_path = udir.join(uniquemodulename('main'))

        for graph in self.translator.graphs:
            self.transform_graph(graph)

        bk = self.translator.annotator.bookkeeper
        ptr = getfunctionptr(bk.getdesc(entry_point).getuniquegraph())

        with self.base_path.new(ext='.ll').open('w') as f:
            # XXX
            f.write('declare i8* @malloc(i64)\n')
            f.write('declare void @free(i8*)\n')
            f.write('declare void @llvm.memcpy.p0i8.p0i8.i64 ('
                    'i8*, i8*, i64, i32, i1)\n')
            f.write('declare void @llvm.memset.p0i8.i64 ('
                    'i8*, i8, i64, i32, i1)\n')
            database = Database(self, f)
            self.entry_point_name = get_repr(ptr).V[1:]
            self.gcpolicy.finish()

    def compile_standalone(self, exe_name):
        pass

    def compile_module(self):
        base_path = str(self.base_path)
        cmdexec('opt -std-compile-opts {0}.ll -o {0}.bc'.format(base_path))
        cmdexec('llc -relocation-model=pic {0}.bc -o {0}.s'.format(base_path))
        cmdexec('llvm-mc {0}.s -filetype=obj -o {0}.o'.format(base_path))
        cmdexec('ld -shared -o {0}.so {0}.o'.format(base_path))

        import ctypes
        cdll = ctypes.CDLL(str(self.base_path) + '.so')
        return getattr(cdll, self.entry_point_name)
