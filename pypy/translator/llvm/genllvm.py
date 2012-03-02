from itertools import count

from py.process import cmdexec
from pypy.objspace.flow.model import mkentrymap, Constant
from pypy.rlib.jit import _we_are_jitted
from pypy.rlib.objectmodel import (ComputedIntSymbolic, CDefinedIntSymbolic,
     malloc_zero_filled, running_on_llinterp)
from pypy.rpython.lltypesystem import llgroup, llmemory, lltype, rffi
from pypy.rpython.memory.gctransform.framework import FrameworkGCTransformer
from pypy.rpython.rmodel import inputconst
from pypy.rpython.typesystem import getfunctionptr
from pypy.translator.gensupp import uniquemodulename
from pypy.translator.unsimplify import remove_double_links
from pypy.tool.udir import udir


class Database(object):
    def __init__(self, genllvm, f):
        self.genllvm = genllvm
        self.f = f
        self.names_counter = {}
        self.types = {}
        self.globals_counter = count()
        self.globals_ = {None: 'null'}
        self.delayed_ptrs = []

    def repr_type(self, type_):
        try:
            return self.types[type_]
        except KeyError:
            self.add_type(type_)
            return self.types[type_]

    def repr_ptr(self, ptr):
        try:
            obj = ptr._obj
        except lltype.DelayedPointer:
            if isinstance(ptr._obj0, str):
                self.delayed_ptrs.append(ptr)
                return '@%s' % ptr._obj0[len('delayed!'):]
            obj = ptr._obj0
        try:
            return self.globals_[obj]
        except KeyError:
            self.add_global(obj._TYPE, obj)
            return self.globals_[obj]

    def _unique(self, name):
        if name not in self.names_counter:
            self.names_counter[name] = 0
            return name
        else:
            ret = '%s_%s' % (name, self.names_counter[name])
            self.names_counter[name] += 1
            return ret

    def add_type(self, type_):
        if isinstance(type_, lltype.FixedSizeArray):
            self.types[type_] = '[%s x %s]' % (type_.length, _T(type_.OF))
        elif isinstance(type_, lltype.Struct):
            self.types[type_] = name = self._unique('%struct.' + type_._name)
            self.f.write('%s = type { %s }\n' % (
                    name, _Tm(type_._flds[fld] for fld in type_._names)))
        elif isinstance(type_, lltype.Array):
            of = _T(type_.OF)
            name = '%array_of_' + of.strip('%').replace('*', '_ptr')
            self.types[type_] = name = self._unique(name)
            self.f.write('%s = type { i64, [0 x %s] }\n' % (name, of))
        elif isinstance(type_, lltype.FuncType):
            self.types[type_] = '%s (%s)' % (_T(type_.RESULT), _Tm(type_.ARGS))
        elif isinstance(type_, lltype.OpaqueType):
            self.types[type_] = 'i8*'
        elif isinstance(type_, llgroup.GroupType):
            self.types[type_] = 'i8*'
        else:
            raise TypeError('type_ is %r' % type_)

    def add_global(self, type_, obj):
        if isinstance(type_, lltype.FuncType):
            name = ('@%s' % obj._name).replace('<', '_').replace('>', '_')
            self.globals_[obj] = name = self._unique(name)
            if getattr(obj, 'external', None) == 'C':
                if name == '@ROUND_UP_FOR_ALLOCATION': # XXX
                    self.f.write('define i64 @ROUND_UP_FOR_ALLOCATION(\n'
                                 '        i64 %tmp, i64 %ignore) {\n'
                                 '    ret i64 %tmp\n'
                                 '}\n')
                    return
                self.f.write('declare %s %s(%s)\n' % (
                        _T(type_.RESULT), name, _Tm(type_.ARGS)))
            else:
                writer = self.genllvm.get_function_writer(name, obj.graph)
                self.f.writelines(writer.lines)
            return

        name = '@global_%s' % next(self.globals_counter)
        if isinstance(type_, lltype.Array):
            typedef = '{ i64, [%s x %s] }' % (len(obj.items), _T(type_.OF))
            self.globals_[obj] = 'bitcast(%s* %s to %s*)' % (
                    typedef, name, _T(type_))
        else:
            typedef = _T(type_)
            self.globals_[obj] = name

        self.f.write('%s = global %s %s\n' % (
                name, typedef, self.repr_obj(type_, obj)))

    def _repr_array(self, flds):
        if all(_V(t, i) == 'null' for t, i in flds):
            return 'zeroinitializer'
        return '[ %s ]' % _TVm(flds)

    def repr_obj(self, type_, obj):
        if isinstance(type_, lltype.FixedSizeArray):
            flds = [(type_.OF, getattr(obj, na)) for na in type_._names]
            return self._repr_array(flds)
        elif isinstance(type_, lltype.Struct):
            flds = [(type_._flds[na], getattr(obj, na)) for na in type_._names]
            if all(_V(t, i) == 'null' for t, i in flds):
                return 'zeroinitializer'
            return '{ %s }' % _TVm(flds)
        elif isinstance(type_, lltype.Array):
            return '{ i64 %s, [%s x %s ] %s }' % (
                    len(obj.items), len(obj.items), _T(type_.OF),
                    self._repr_array([(type_.OF, i) for i in obj.items]))
        elif isinstance(type_, lltype.OpaqueType):
            return 'null'
        elif isinstance(type_, llgroup.GroupType):
            return 'null'
        else:
            raise TypeError('type_ is %r' % type_)


def repr_void(value):
    if value is None:
        return 'null'
    raise TypeError

def repr_number(value):
    if isinstance(value, (int, long)):
        return str(value)

    if isinstance(value, ComputedIntSymbolic):
        return value.compute_fn()
    elif isinstance(value, llmemory.AddressOffset):
        return '0' # XXX
        raise NotImplementedError
    elif isinstance(value, llgroup.GroupMemberOffset):
        return value.index
    elif isinstance(value, CDefinedIntSymbolic):
        if value is malloc_zero_filled:
            return '1'
        elif value is _we_are_jitted:
            return '0'
        elif value is running_on_llinterp:
            return '0'
    raise NotImplementedError(value)

def repr_address(value):
    if value.ptr is None:
        return 'null'
    return "bitcast(%s to i8*)" % TV(C(value.ptr))

PRIMITIVES = {
    lltype.Void: ('void', repr_void),
    lltype.Signed: ('i64', repr_number),
    lltype.Unsigned: ('i64', repr_number),
    lltype.Char: ('i8', lambda x: str(ord(x))),
    lltype.Bool: ('i1', lambda x: 'true' if x else 'false'),
    lltype.Float: ('double', repr),
    lltype.SingleFloat: ('float', repr),
    lltype.LongFloat: ('x86_fp80', repr),
    llmemory.Address: ('i8*', repr_address)
}
for type_ in rffi.NUMBER_TYPES:
    if type_ not in PRIMITIVES:
        PRIMITIVES[type_] = ('i%s' % (rffi.sizeof(type_) * 8), repr_number)

def _T(type_):
    """Represent LLType `type_`."""
    if isinstance(type_, lltype.Primitive):
        return PRIMITIVES[type_][0]
    elif isinstance(type_, lltype.Ptr):
        return '%s*' % _T(type_.TO)
    else:
        return database.repr_type(type_)

def T(variable_or_const):
    """Represent LLType of `variable_or_const`."""
    return _T(variable_or_const.concretetype)

def _V(type_, value):
    """Represent LLValue `value` of type `type_`."""
    if isinstance(type_, lltype.Primitive):
        return PRIMITIVES[type_][1](value)
    elif isinstance(type_, lltype.Ptr):
        return database.repr_ptr(value)
    else:
        return database.repr_obj(value._TYPE, value)

def V(variable_or_const):
    """Represent LLValue of `variable_or_const`."""
    if isinstance(variable_or_const, Constant):
        return _V(variable_or_const.concretetype, variable_or_const.value)
    return '%%%s' % variable_or_const.name

def TV(variable_or_const):
    """Same as '%s %s' % (T(`variable_or_const`), V(`variable_or_const`))."""
    return '%s %s' % (_T(variable_or_const.concretetype), V(variable_or_const))

def _Tm(types):
    """Represent multiple types. `types` is an iterable of LLTypes."""
    return ', '.join(_T(type_) for type_ in types if type_ is not lltype.Void)

def Vm(vals):
    """Represent multiple values. `vals` is an iterable of LLValues."""
    return ', '.join(V(val) for val in vals)

def _TVm(vocs):
    """
    Represent multiple types and values. `vocs` is an iterable of
    (LLType, LLValue) pairs.
    """
    return ', '.join('%s %s' % (_T(type_), _V(type_, val))
                     for type_, val in vocs if type_ is not lltype.Void)

def TVm(vocs):
    """
    Represent multiple types and values. `vocs` is an iterable of LLValues.
    """
    return ', '.join(TV(voc) for voc in vocs
                     if voc.concretetype is not lltype.Void)

def C(value):
    """Return `value` as Constant."""
    return inputconst(lltype.typeOf(value), value)


OPS = {
        'int_add_ovf': 'add', # XXX check for overflow
        'int_mul_ovf': 'mul', # XXX check for overflow
}
for type_ in ['int', 'uint', 'llong', 'ullong']:
    OPS['%s_lshift' % type_] = 'shl'
    OPS['%s_rshift' % type_] = 'lshr' if type_[0] == 'u' else 'ashr'
    OPS['%s_floordiv' % type_] = 'udiv' if type_[0] == 'u' else 'sdiv'
    OPS['%s_mod' % type_] = 'urem' if type_[0] == 'u' else 'srem'
    for op in ['add', 'sub', 'mul', 'and', 'or', 'xor']:
        OPS['%s_%s' % (type_, op)] = op

for type_ in ['float']:
    for op in ['add', 'sub', 'mul', 'div']:
        OPS['%s_%s' % (type_, op)] = 'f%s' % op

for type_, prefix in [('char', 'u'), ('unichar', 'u'), ('int', 's'),
                      ('uint', 'u'), ('llong', 's'), ('ullong', 'u'),
                      ('adr', 's'), ('ptr', 's')]:
    OPS['%s_eq' % type_] = 'icmp eq'
    OPS['%s_ne' % type_] = 'icmp ne'
    for op in ['gt', 'ge', 'lt', 'le']:
        OPS['%s_%s' % (type_, op)] = 'icmp %s%s' % (prefix, op)

for type_ in ['float']:
    for op in ['eq', 'ne', 'gt', 'ge', 'lt', 'le']:
        OPS['%s_%s' % (type_, op)] = 'fcmp o%s' % op


class FunctionWriter(object):
    def __init__(self):
        self.lines = []
        self.tmp_counter = count()

    def w(self, line, indent='    '):
        self.lines.append('%s%s\n' % (indent, line))

    def write_graph(self, name, graph):
        self.w('define %s %s(%s) {' % (T(graph.getreturnvar()), name,
                                       TVm(graph.getargs())), '')

        self.entrymap = mkentrymap(graph)
        self.block_to_name = dict(
                (bl, 'block%s' % i) for i, bl in enumerate(graph.iterblocks()))
        for block in graph.iterblocks():
            self.w('%s:' % self.block_to_name[block], '  ')
            if block is not graph.startblock:
                self.write_phi_nodes(block)
            self.write_operations(block)
            self.write_branches(block)
        self.w('}', '')

    def write_phi_nodes(self, block):
        for i, arg in enumerate(block.inputargs):
            if arg.concretetype == lltype.Void:
                continue
            argsstr = ', '.join('[%s, %%%s]' %
                    (V(l.args[i]), self.block_to_name[l.prevblock])
                    for l in self.entrymap[block] if l.prevblock is not None)
            self.w('%s = phi %s %s' % (V(arg), T(arg), argsstr))

    def write_operations(self, block):
        for op in block.operations:
            self.w('; %s' % op)
            opname = op.opname
            if opname in OPS:
                self.w('%s = %s %s %s' % (
                        V(op.result), OPS[opname], T(op.args[0]), Vm(op.args)))
            elif opname.startswith('cast_'):
                if opname == 'cast_adr_to_int':
                    self._cast(op.result, op.args[0], 'ptrtoint')
                elif opname == 'cast_int_to_adr':
                    self._cast(op.result, op.args[0], 'inttoptr')
                else:
                    self._cast(op.result, op.args[0])
            else:
                func = getattr(self, 'op_' + opname, None)
                if func is not None:
                    func(op.result, *op.args)
                else:
                    raise NotImplementedError(op)

    def op_debug_print(self, result, *args):
        pass

    def op_debug_assert(self, result, *args):
        pass

    def op_debug_llinterpcall(self, result, *args):
        if result.concretetype is not lltype.Void:
            self.w('%s = bitcast %s undef to %s' % (
                    V(result), T(result), T(result)))

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

    def _ptr_or_adr(self, var):
        return (isinstance(var.concretetype, lltype.Ptr) or
                var.concretetype is llmemory.Address)

    def _cast(self, to, fr, op=None):
        if op is None:
            if ((fr.concretetype is to.concretetype) or
                (self._ptr_or_adr(fr) and self._ptr_or_adr(to))):
                op = 'bitcast'
            else:
                fr_size = rffi.sizeof(fr.concretetype)
                to_size = rffi.sizeof(to.concretetype)
                if fr_size == to_size:
                    op = 'bitcast'
                elif fr_size > to_size:
                    op = 'trunc'
                elif fr_size < to_size:
                    if rffi.size_and_sign(fr.concretetype)[1]:
                        op = 'sext'
                    else:
                        op = 'zext'
        self.w('%s = %s %s %s to %s' % (V(to), op, T(fr), V(fr), T(to)))
    op_raw_malloc_usage = _cast

    def op_force_cast(self, result, var):
        r_ptr = self._ptr_or_adr(result)
        v_ptr = self._ptr_or_adr(var)
        if r_ptr and v_ptr:
            self._cast(result, var, 'bitcast')
        elif r_ptr:
            self._cast(result, var, 'inttoptr')
        elif v_ptr:
            self._cast(result, var, 'ptrtoint')
        else:
            self._cast(result, var)

    def op_direct_call(self, result, fn, *args):
        if result.concretetype is lltype.Void:
            self.w('call void %s(%s)' % (V(fn), TVm(args)))
        else:
            if (isinstance(result.concretetype, lltype.Ptr) and
                isinstance(result.concretetype.TO, lltype.FuncType)):
                self.w('%s = call %s %s(%s)' %
                        (V(result), T(fn), V(fn), TVm(args)))
            else:
                self.w('%s = call %s %s(%s)' %
                        (V(result), T(result), V(fn), TVm(args)))
    op_indirect_call = op_direct_call

    def _get_field_ptr(self, ptr, field, target_var):
        self.w('%s = getelementptr %s %s, i64 0, i32 %s' % (
                target_var, T(ptr), V(ptr),
                ptr.concretetype.TO._names_without_voids().index(field.value)))

    def op_getsubstruct(self, result, var, field):
        self._get_field_ptr(var, field, V(result))

    def op_direct_fieldptr(self, result, var, field):
        t = '%%tmp%s' % next(self.tmp_counter)
        self._get_field_ptr(var, field, t)
        self.w('%s = bitcast %s %s to %s' % (
                V(result), _T(result.concretetype.TO.OF)+'*', t, T(result)))

    def op_getfield(self, result, var, field):
        t = '%%tmp%s' % next(self.tmp_counter)
        self._get_field_ptr(var, field, t)
        self.w('%s = load %s %s' % (V(result), T(result)+'*', t))
    op_bare_getfield = op_getfield

    def op_setfield(self, result, var, field, value):
        t = '%%tmp%s' % next(self.tmp_counter)
        self._get_field_ptr(var, field, t)
        self.w('store %s, %s %s' % (TV(value), T(value)+'*', t))
    op_bare_setfield = op_setfield

    def _get_item_ptr(self, ptr, index, target_var):
        if isinstance(ptr.concretetype.TO, lltype.FixedSizeArray):
            self.w('%s = getelementptr %s %s, i64 0, i64 %s' % (
                    target_var, T(ptr), V(ptr), V(index)))
        else:
            self.w('%s = getelementptr %s %s, i64 0, i32 1, i64 %s' % (
                    target_var, T(ptr), V(ptr), V(index)))

    def op_getarraysubstruct(self, result, var, index):
        self._get_item_ptr(var, index, V(result))

    def op_getarrayitem(self, result, var, index):
        t = '%%tmp%s' % next(self.tmp_counter)
        self._get_item_ptr(var, index, t)
        self.w('%s = load %s %s' % (V(result), T(result)+'*', t))
    op_bare_getarrayitem = op_getarrayitem

    def op_setarrayitem(self, result, var, index, value):
        t = '%%tmp%s' % next(self.tmp_counter)
        self._get_item_ptr(var, index, t)
        self.w('store %s, %s %s' % (TV(value), T(value)+'*', t))
    op_bare_setarrayitem = op_setarrayitem

    def op_getarraysize(self, result, var):
        type_ = var.concretetype.TO
        assert (isinstance(type_, lltype.Array) and
                not type_._hints.get("nolength", False))

        t = '%%tmp%s' % next(self.tmp_counter)
        self.w('%s = getelementptr %s, i64 0, i32 0' % (t, TV(var)))
        self.w('%s = load i64* %s' % (V(result), t))

    def op_int_is_true(self, result, var):
        self.w('%s = icmp ne i64 %s, 0' % (V(result), V(var)))

    def op_int_neg(self, result, var):
        self.w('%s = sub %s 0, %s' % (V(result), T(var), V(var)))

    def op_ptr_iszero(self, result, var):
        self.w('%s = icmp eq %s %s, null' % (V(result), T(var), V(var)))

    def op_ptr_nonzero(self, result, var):
        self.w('%s = icmp ne %s %s, null' % (V(result), T(var), V(var)))

    def op_adr_delta(self, result, arg1, arg2):
        t1 = '%%tmp%s' % next(self.tmp_counter)
        t2 = '%%tmp%s' % next(self.tmp_counter)
        self.w('%s = ptrtoint %s %s to i64' % (t1, T(arg1), V(arg1)))
        self.w('%s = ptrtoint %s %s to i64' % (t2, T(arg2), V(arg2)))
        self.w('%s = sub i64 %s, %s' % (V(result), t1, t2))

    def _adr_op(int_op):
        def f(self, result, arg1, arg2):
            t = '%%tmp%s' % next(self.tmp_counter)
            tr = '%%tmp%s' % next(self.tmp_counter)
            self.w('%s = ptrtoint %s %s to i64' % (t, T(arg1), V(arg1)))
            self.w('%s = %s i64 %s, %s' % (tr, int_op, t, V(arg2)))
            self.w('%s = inttoptr i64 %s to %s' % (V(result), tr, T(result)))
        return f

    op_adr_add = _adr_op('add')
    op_adr_sub = _adr_op('sub')

    def op_raw_malloc(self, result, size):
        self.w('%s = call %s @malloc(%s)' % (V(result), T(result), TV(size)))

    def _get_addr(self, type_, addr, incr):
        t1 = '%%tmp%s' % next(self.tmp_counter)
        t2 = '%%tmp%s' % next(self.tmp_counter)
        tt = T(type_)+'*'
        self.w('%s = bitcast %s to %s' % (t1, TV(addr), tt))
        self.w('%s = getelementptr %s %s, i64 %s' % (t2, tt, t1, incr))
        return '%s %s' % (tt, t2)

    def op_raw_load(self, result, addr, _, incr):
        self.w('%s = load %s' % (V(result), self._get_addr(result,addr, incr)))

    def op_raw_store(self, result, addr, _, incr, value):
        self.w('store %s, %s' % (TV(value), self._get_addr(value, addr, incr)))

    def op_raw_memclear(self, result, pointer, size):
        self.w('call void @llvm.memset.p0i8.i64 (%s, i8 0, %s, i32 0, i1 0)' %
                (TV(pointer), TV(size)))

    def op_raw_memcopy(self, result, source, dest, size):
        self.w('call void @llvm.memcpy.p0i8.p0i8.i64 (%s, %s, %s, i32 0, i1 0)'
                % (TV(dest), TV(source), TV(size)))

    def op_raw_free(self, result, var):
        self.w('call void @free(%s)' % TV(var))

    def op_extract_ushort(self, result, value):
        self.w('%s = trunc %s to %s' % (V(result), TV(value), T(result)))

    def op_combine_ushort(self, result, ushort, rest):
        t = '%%tmp%s' % next(self.tmp_counter)
        self.w('%s = sext %s to %s' % (t, TV(ushort), T(rest)))
        self.w('%s = or %s %s, %s' % (V(result), T(result), t, V(rest)))

    def op_get_group_member(self, result, groupptr, compactoffset):
        t1 = '%%tmp%s' % next(self.tmp_counter)
        t2 = '%%tmp%s' % next(self.tmp_counter)
        tr = '%%tmp%s' % next(self.tmp_counter)
        self.w('%s = ptrtoint %s %s to i64' % (t1, T(groupptr), V(groupptr)))
        self.w('%s = sext %s to i64' % (t2, TV(compactoffset)))
        self.w('%s = add i64 %s, %s' % (tr, t1, t2))
        self.w('%s = inttoptr i64 %s to %s' % (V(result), tr, T(result)))

    def op_gc_gettypeptr_group(self, result, v_obj, grpptr, skipoffset, vtableinfo):
        # XXX
        self.w('%s = inttoptr i64 0 to %s' % (V(result), T(result)))

    def op_gc_reload_possibly_moved(self, result, v_newaddr, v_targetvar):
        pass

    def op_keepalive(self, result, var):
        pass

    def write_branches(self, block):
        if len(block.exits) == 0:
            self.write_returnblock(block)
        elif len(block.exits) == 1:
            self.w('br label %%%s' % self.block_to_name[block.exits[0].target])
        elif len(block.exits) == 2:
            assert block.exitswitch.concretetype is lltype.Bool
            for link in block.exits:
                if link.llexitcase:
                    true = self.block_to_name[link.target]
                else:
                    false = self.block_to_name[link.target]
            self.w('br i1 %s, label %%%s, label %%%s' % (
                    V(block.exitswitch), true, false))
        else:
            raise NotImplementedError

    def write_returnblock(self, block):
        ret = block.inputargs[0]
        if ret.concretetype is lltype.Void:
            self.w('ret void')
        else:
            self.w('ret %s %s' % (T(ret), V(ret)))


class GCPolicy(object):
    def __init__(self, genllvm):
        self.genllvm = genllvm

    def transform_graph(self, graph):
        pass

    def finish(self):
        assert not database.delayed_ptrs


class FrameworkGCPolicy(GCPolicy):
    def __init__(self, genllvm):
        self.genllvm = genllvm
        self.gctransformer = FrameworkGCTransformer(genllvm.translator)

    def transform_graph(self, graph):
        self.gctransformer.transform_graph(graph)

    def finish(self):
        while database.delayed_ptrs:
            self.gctransformer.finish_helpers()

            delayed_ptrs = database.delayed_ptrs
            database.delayed_ptrs = []
            for ptr in delayed_ptrs:
                _V(lltype.typeOf(ptr), ptr)

            list(self.gctransformer.get_finish_tables())


class GenLLVM(object):
    def __init__(self, translator, standalone):
        self.translator = translator

        self.exctransformer = translator.getexceptiontransformer()
        self.gcpolicy = {
            'none': GCPolicy,
            'framework': FrameworkGCPolicy
        }[translator.config.translation.gctransformer](self)

    def get_function_writer(self, name, graph):
        self.exctransformer.create_exception_handling(graph)
        self.gcpolicy.transform_graph(graph)
        remove_double_links(self.translator.annotator, graph)
        writer = FunctionWriter()
        writer.write_graph(name, graph)
        return writer

    def gen_source(self, entry_point):
        global database

        self.entry_point = entry_point
        self.base_path = udir.join(uniquemodulename('main'))

        bk = self.translator.annotator.bookkeeper
        ptr = getfunctionptr(bk.getdesc(entry_point).getuniquegraph())

        with self.base_path.new(ext='.ll').open('w') as f:
            # XXX
            f.write('declare void @llvm.memcpy.p0i8.p0i8.i64 ('
                    'i8*, i8*, i64, i32, i1)\n')
            f.write('declare void @llvm.memset.p0i8.i64 ('
                    'i8*, i8, i64, i32, i1)\n')
            database = Database(self, f)
            self.c_entry_point_name = V(C(ptr))[1:]
            self.gcpolicy.finish()

    def compile_standalone(self, exe_name):
        pass

    def compile_module(self):
        base_path = str(self.base_path)
        cmdexec('opt -std-compile-opts %s.ll -o %s.bc' % ((base_path,)*2))
        cmdexec('llc -relocation-model=pic %s.bc -o %s.s' % ((base_path,)*2))
        cmdexec('llvm-mc %s.s -filetype=obj -o %s.o' % ((base_path,)*2))
        cmdexec('ld -shared -o %s.so %s.o' % ((base_path,)*2))

        import ctypes
        cdll = ctypes.CDLL(str(self.base_path) + '.so')
        return getattr(cdll, self.c_entry_point_name)
