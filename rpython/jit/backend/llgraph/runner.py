import py, weakref
from rpython.jit.backend import model
from rpython.jit.backend.llgraph import support
from rpython.jit.metainterp.history import AbstractDescr
from rpython.jit.metainterp.history import Const, getkind
from rpython.jit.metainterp.history import INT, REF, FLOAT, VOID
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.codewriter import longlong, heaptracker
from rpython.jit.codewriter.effectinfo import EffectInfo

from rpython.rtyper.llinterp import LLInterpreter, LLException
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi, rclass, rstr

from rpython.rlib.rarithmetic import ovfcheck, r_uint, r_ulonglong
from rpython.rlib.rtimer import read_timestamp

class LLTrace(object):
    has_been_freed = False
    invalid = False

    def __init__(self, inputargs, operations):
        # We need to clone the list of operations because the
        # front-end will mutate them under our feet again.  We also
        # need to make sure things get freed.
        def mapping(box, _cache={}):
            if isinstance(box, Const) or box is None:
                return box
            try:
                newbox = _cache[box]
            except KeyError:
                newbox = _cache[box] = box.__class__()
            return newbox
        #
        self.inputargs = map(mapping, inputargs)
        self.operations = []
        for op in operations:
            if op.getdescr() is not None:
                if op.is_guard() or op.getopnum() == rop.FINISH:
                    newdescr = op.getdescr()
                else:
                    newdescr = WeakrefDescr(op.getdescr())
            else:
                newdescr = None
            newop = op.copy_and_change(op.getopnum(),
                                       map(mapping, op.getarglist()),
                                       mapping(op.result),
                                       newdescr)
            if op.getfailargs() is not None:
                newop.setfailargs(map(mapping, op.getfailargs()))
            self.operations.append(newop)

class WeakrefDescr(AbstractDescr):
    def __init__(self, realdescr):
        self.realdescrref = weakref.ref(realdescr)
        self.final_descr = getattr(realdescr, 'final_descr', False)

class ExecutionFinished(Exception):
    def __init__(self, deadframe):
        self.deadframe = deadframe

class Jump(Exception):
    def __init__(self, jump_target, args):
        self.jump_target = jump_target
        self.args = args

class CallDescr(AbstractDescr):
    def __init__(self, RESULT, ARGS, extrainfo):
        self.RESULT = RESULT
        self.ARGS = ARGS
        self.extrainfo = extrainfo

    def __repr__(self):
        return 'CallDescr(%r, %r, %r)' % (self.RESULT, self.ARGS,
                                          self.extrainfo)

    def get_extra_info(self):
        return self.extrainfo

    def get_arg_types(self):
        return ''.join([getkind(ARG)[0] for ARG in self.ARGS])

    def get_result_type(self):
        return getkind(self.RESULT)[0]

class SizeDescr(AbstractDescr):
    def __init__(self, S):
        self.S = S

    def as_vtable_size_descr(self):
        return self

    def count_fields_if_immutable(self):
        return heaptracker.count_fields_if_immutable(self.S)

    def __repr__(self):
        return 'SizeDescr(%r)' % (self.S,)

class FieldDescr(AbstractDescr):
    def __init__(self, S, fieldname):
        self.S = S
        self.fieldname = fieldname
        self.FIELD = getattr(S, fieldname)

    def get_vinfo(self):
        return self.vinfo

    def __repr__(self):
        return 'FieldDescr(%r, %r)' % (self.S, self.fieldname)

    def sort_key(self):
        return self.fieldname

    def is_pointer_field(self):
        return getkind(self.FIELD) == 'ref'

    def is_float_field(self):
        return getkind(self.FIELD) == 'float'

    def is_field_signed(self):
        return _is_signed_kind(self.FIELD)

def _is_signed_kind(TYPE):
    return (TYPE is not lltype.Bool and isinstance(TYPE, lltype.Number) and
            rffi.cast(TYPE, -1) == -1)

class ArrayDescr(AbstractDescr):
    def __init__(self, A):
        self.A = self.OUTERA = A
        if isinstance(A, lltype.Struct):
            self.A = A._flds[A._arrayfld]

    def __repr__(self):
        return 'ArrayDescr(%r)' % (self.OUTERA,)

    def is_array_of_pointers(self):
        return getkind(self.A.OF) == 'ref'

    def is_array_of_floats(self):
        return getkind(self.A.OF) == 'float'

    def is_item_signed(self):
        return _is_signed_kind(self.A.OF)

    def is_array_of_structs(self):
        return isinstance(self.A.OF, lltype.Struct)

class InteriorFieldDescr(AbstractDescr):
    def __init__(self, A, fieldname):
        self.A = A
        self.fieldname = fieldname
        self.FIELD = getattr(A.OF, fieldname)

    def __repr__(self):
        return 'InteriorFieldDescr(%r, %r)' % (self.A, self.fieldname)

    def sort_key(self):
        return self.fieldname

    def is_pointer_field(self):
        return getkind(self.FIELD) == 'ref'

    def is_float_field(self):
        return getkind(self.FIELD) == 'float'

_example_res = {'v': None,
                'r': lltype.nullptr(llmemory.GCREF.TO),
                'i': 0,
                'f': 0.0}

class LLGraphCPU(model.AbstractCPU):
    from rpython.jit.metainterp.typesystem import llhelper as ts
    supports_floats = True
    supports_longlong = r_uint is not r_ulonglong
    supports_singlefloats = True
    translate_support_code = False
    is_llgraph = True

    def __init__(self, rtyper, stats=None, *ignored_args, **kwds):
        model.AbstractCPU.__init__(self)
        self.rtyper = rtyper
        self.llinterp = LLInterpreter(rtyper)
        self.descrs = {}
        class MiniStats:
            pass
        self.stats = stats or MiniStats()
        self.vinfo_for_tests = kwds.get('vinfo_for_tests', None)

    def compile_loop(self, inputargs, operations, looptoken, log=True,
                     name='', logger=None):
        clt = model.CompiledLoopToken(self, looptoken.number)
        looptoken.compiled_loop_token = clt
        lltrace = LLTrace(inputargs, operations)
        clt._llgraph_loop = lltrace
        clt._llgraph_alltraces = [lltrace]
        self._record_labels(lltrace)

    def compile_bridge(self, faildescr, inputargs, operations,
                       original_loop_token, log=True, logger=None):
        clt = original_loop_token.compiled_loop_token
        clt.compiling_a_bridge()
        lltrace = LLTrace(inputargs, operations)
        faildescr._llgraph_bridge = lltrace
        clt._llgraph_alltraces.append(lltrace)
        self._record_labels(lltrace)

    def _record_labels(self, lltrace):
        for i, op in enumerate(lltrace.operations):
            if op.getopnum() == rop.LABEL:
                _getdescr(op)._llgraph_target = (lltrace, i)

    def invalidate_loop(self, looptoken):
        for trace in looptoken.compiled_loop_token._llgraph_alltraces:
            trace.invalid = True

    def redirect_call_assembler(self, oldlooptoken, newlooptoken):
        oldtrace = oldlooptoken.compiled_loop_token._llgraph_loop
        newtrace = newlooptoken.compiled_loop_token._llgraph_loop
        OLD = [box.type for box in oldtrace.inputargs]
        NEW = [box.type for box in newtrace.inputargs]
        assert OLD == NEW
        assert not hasattr(oldlooptoken, '_llgraph_redirected')
        oldlooptoken.compiled_loop_token._llgraph_redirected = True
        oldlooptoken.compiled_loop_token._llgraph_loop = newtrace
        alltraces = newlooptoken.compiled_loop_token._llgraph_alltraces
        oldlooptoken.compiled_loop_token._llgraph_alltraces = alltraces

    def free_loop_and_bridges(self, compiled_loop_token):
        for c in compiled_loop_token._llgraph_alltraces:
            c.has_been_freed = True
        compiled_loop_token._llgraph_alltraces = []
        compiled_loop_token._llgraph_loop = None
        model.AbstractCPU.free_loop_and_bridges(self, compiled_loop_token)

    def make_execute_token(self, *argtypes):
        return self._execute_token

    def _execute_token(self, loop_token, *args):
        lltrace = loop_token.compiled_loop_token._llgraph_loop
        frame = LLFrame(self, lltrace.inputargs, args)
        try:
            frame.execute(lltrace)
            assert False
        except ExecutionFinished, e:
            return e.deadframe

    def get_int_value(self, deadframe, index):
        v = deadframe._values[index]
        assert lltype.typeOf(v) == lltype.Signed
        return v

    def get_ref_value(self, deadframe, index):
        v = deadframe._values[index]
        assert lltype.typeOf(v) == llmemory.GCREF
        return v

    def get_float_value(self, deadframe, index):
        v = deadframe._values[index]
        assert lltype.typeOf(v) == longlong.FLOATSTORAGE
        return v

    def get_latest_descr(self, deadframe):
        return deadframe._latest_descr

    def grab_exc_value(self, deadframe):
        if deadframe._last_exception is not None:
            result = deadframe._last_exception.args[1]
            gcref = lltype.cast_opaque_ptr(llmemory.GCREF, result)
        else:
            gcref = lltype.nullptr(llmemory.GCREF.TO)
        return gcref

    def force(self, force_token):
        frame = force_token
        assert isinstance(frame, LLFrame)
        assert frame.forced_deadframe is None
        values = []
        for box in frame.force_guard_op.getfailargs():
            if box is not None:
                if box is not frame.current_op.result:
                    value = frame.env[box]
                else:
                    value = box.value    # 0 or 0.0 or NULL
            else:
                value = None
            values.append(value)
        frame.forced_deadframe = LLDeadFrame(
            _getdescr(frame.force_guard_op), values)
        return frame.forced_deadframe

    def set_savedata_ref(self, deadframe, data):
        deadframe._saved_data = data

    def get_savedata_ref(self, deadframe):
        assert deadframe._saved_data is not None
        return deadframe._saved_data

    # ------------------------------------------------------------

    def calldescrof(self, FUNC, ARGS, RESULT, effect_info):
        key = ('call', getkind(RESULT),
               tuple([getkind(A) for A in ARGS]),
               effect_info)
        try:
            return self.descrs[key]
        except KeyError:
            descr = CallDescr(RESULT, ARGS, effect_info)
            self.descrs[key] = descr
            return descr

    def sizeof(self, S):
        key = ('size', S)
        try:
            return self.descrs[key]
        except KeyError:
            descr = SizeDescr(S)
            self.descrs[key] = descr
            return descr

    def fielddescrof(self, S, fieldname):
        key = ('field', S, fieldname)
        try:
            return self.descrs[key]
        except KeyError:
            descr = FieldDescr(S, fieldname)
            self.descrs[key] = descr
            if self.vinfo_for_tests is not None:
                descr.vinfo = self.vinfo_for_tests
            return descr

    def arraydescrof(self, A):
        key = ('array', A)
        try:
            return self.descrs[key]
        except KeyError:
            descr = ArrayDescr(A)
            self.descrs[key] = descr
            return descr

    def interiorfielddescrof(self, A, fieldname):
        key = ('interiorfield', A, fieldname)
        try:
            return self.descrs[key]
        except KeyError:
            descr = InteriorFieldDescr(A, fieldname)
            self.descrs[key] = descr
            return descr

    def _calldescr_dynamic_for_tests(self, atypes, rtype,
                                     abiname='FFI_DEFAULT_ABI'):
        # XXX WTF is that and why it breaks all abstractions?
        from rpython.jit.backend.llsupport import ffisupport
        return ffisupport.calldescr_dynamic_for_tests(self, atypes, rtype,
                                                      abiname)

    def calldescrof_dynamic(self, cif_description, extrainfo):
        # XXX WTF, this is happy nonsense
        from rpython.jit.backend.llsupport.ffisupport import get_ffi_type_kind
        from rpython.jit.backend.llsupport.ffisupport import UnsupportedKind
        ARGS = []
        try:
            for itp in range(cif_description.nargs):
                arg = cif_description.atypes[itp]
                kind = get_ffi_type_kind(self, arg)
                if kind != VOID:
                    ARGS.append(support.kind2TYPE[kind[0]])
            RESULT = support.kind2TYPE[get_ffi_type_kind(self, cif_description.rtype)[0]]
        except UnsupportedKind:
            return None
        key = ('call_dynamic', RESULT, tuple(ARGS),
               extrainfo, cif_description.abi)
        try:
            return self.descrs[key]
        except KeyError:
            descr = CallDescr(RESULT, ARGS, extrainfo)
            self.descrs[key] = descr
            return descr

    # ------------------------------------------------------------

    def maybe_on_top_of_llinterp(self, func, args, RESULT):
        ptr = llmemory.cast_int_to_adr(func).ptr
        if hasattr(ptr._obj, 'graph'):
            res = self.llinterp.eval_graph(ptr._obj.graph, args)
        else:
            res = ptr._obj._callable(*args)
        if RESULT is lltype.Void:
            return None
        return support.cast_result(RESULT, res)

    def _do_call(self, func, args_i, args_r, args_f, calldescr):
        TP = llmemory.cast_int_to_adr(func).ptr._obj._TYPE
        args = support.cast_call_args(TP.ARGS, args_i, args_r, args_f)
        return self.maybe_on_top_of_llinterp(func, args, TP.RESULT)

    bh_call_i = _do_call
    bh_call_r = _do_call
    bh_call_f = _do_call
    bh_call_v = _do_call

    def bh_getfield_gc(self, p, descr):
        p = support.cast_arg(lltype.Ptr(descr.S), p)
        return support.cast_result(descr.FIELD, getattr(p, descr.fieldname))

    bh_getfield_gc_pure = bh_getfield_gc
    bh_getfield_gc_i = bh_getfield_gc
    bh_getfield_gc_r = bh_getfield_gc
    bh_getfield_gc_f = bh_getfield_gc

    bh_getfield_raw = bh_getfield_gc
    bh_getfield_raw_pure = bh_getfield_raw
    bh_getfield_raw_i = bh_getfield_raw
    bh_getfield_raw_r = bh_getfield_raw
    bh_getfield_raw_f = bh_getfield_raw

    def bh_setfield_gc(self, p, newvalue, descr):
        p = support.cast_arg(lltype.Ptr(descr.S), p)
        setattr(p, descr.fieldname, support.cast_arg(descr.FIELD, newvalue))

    bh_setfield_gc_i = bh_setfield_gc
    bh_setfield_gc_r = bh_setfield_gc
    bh_setfield_gc_f = bh_setfield_gc

    bh_setfield_raw   = bh_setfield_gc
    bh_setfield_raw_i = bh_setfield_raw
    bh_setfield_raw_f = bh_setfield_raw

    def bh_arraylen_gc(self, a, descr):
        array = a._obj.container
        if descr.A is not descr.OUTERA:
            array = getattr(array, descr.OUTERA._arrayfld)
        return array.getlength()

    def bh_getarrayitem_gc(self, a, index, descr):
        a = support.cast_arg(lltype.Ptr(descr.A), a)
        array = a._obj
        return support.cast_result(descr.A.OF, array.getitem(index))

    bh_getarrayitem_gc_pure = bh_getarrayitem_gc
    bh_getarrayitem_gc_i = bh_getarrayitem_gc
    bh_getarrayitem_gc_r = bh_getarrayitem_gc
    bh_getarrayitem_gc_f = bh_getarrayitem_gc

    bh_getarrayitem_raw = bh_getarrayitem_gc
    bh_getarrayitem_raw_pure = bh_getarrayitem_raw
    bh_getarrayitem_raw_i = bh_getarrayitem_raw
    bh_getarrayitem_raw_r = bh_getarrayitem_raw
    bh_getarrayitem_raw_f = bh_getarrayitem_raw

    def bh_setarrayitem_gc(self, a, index, item, descr):
        a = support.cast_arg(lltype.Ptr(descr.A), a)
        array = a._obj
        array.setitem(index, support.cast_arg(descr.A.OF, item))

    bh_setarrayitem_gc_i = bh_setarrayitem_gc
    bh_setarrayitem_gc_r = bh_setarrayitem_gc
    bh_setarrayitem_gc_f = bh_setarrayitem_gc

    bh_setarrayitem_raw   = bh_setarrayitem_gc
    bh_setarrayitem_raw_i = bh_setarrayitem_raw
    bh_setarrayitem_raw_r = bh_setarrayitem_raw
    bh_setarrayitem_raw_f = bh_setarrayitem_raw

    def bh_getinteriorfield_gc(self, a, index, descr):
        array = a._obj.container
        return support.cast_result(descr.FIELD,
                          getattr(array.getitem(index), descr.fieldname))

    bh_getinteriorfield_gc_i = bh_getinteriorfield_gc
    bh_getinteriorfield_gc_r = bh_getinteriorfield_gc
    bh_getinteriorfield_gc_f = bh_getinteriorfield_gc

    def bh_setinteriorfield_gc(self, a, index, item, descr):
        array = a._obj.container
        setattr(array.getitem(index), descr.fieldname,
                support.cast_arg(descr.FIELD, item))

    bh_setinteriorfield_gc_i = bh_setinteriorfield_gc
    bh_setinteriorfield_gc_r = bh_setinteriorfield_gc
    bh_setinteriorfield_gc_f = bh_setinteriorfield_gc

    def bh_raw_load_i(self, struct, offset, descr):
        ll_p = rffi.cast(rffi.CCHARP, struct)
        ll_p = rffi.cast(lltype.Ptr(descr.A), rffi.ptradd(ll_p, offset))
        value = ll_p[0]
        return support.cast_result(descr.A.OF, value)

    def bh_raw_load_f(self, struct, offset, descr):
        ll_p = rffi.cast(rffi.CCHARP, struct)
        ll_p = rffi.cast(rffi.CArrayPtr(longlong.FLOATSTORAGE),
                         rffi.ptradd(ll_p, offset))
        return ll_p[0]

    def bh_raw_load(self, struct, offset, descr):
        if descr.A.OF == lltype.Float:
            return self.bh_raw_load_f(struct, offset, descr)
        else:
            return self.bh_raw_load_i(struct, offset, descr)

    def unpack_arraydescr_size(self, arraydescr):
        from rpython.jit.backend.llsupport.symbolic import get_array_token
        from rpython.jit.backend.llsupport.descr import get_type_flag, FLAG_SIGNED
        assert isinstance(arraydescr, ArrayDescr)
        basesize, itemsize, _ = get_array_token(arraydescr.A, False)
        flag = get_type_flag(arraydescr.A.OF)
        is_signed = (flag == FLAG_SIGNED)
        return basesize, itemsize, is_signed

    def bh_raw_store_i(self, struct, offset, newvalue, descr):
        ll_p = rffi.cast(rffi.CCHARP, struct)
        ll_p = rffi.cast(lltype.Ptr(descr.A), rffi.ptradd(ll_p, offset))
        if descr.A.OF == lltype.SingleFloat:
            newvalue = longlong.int2singlefloat(newvalue)
        ll_p[0] = rffi.cast(descr.A.OF, newvalue)

    def bh_raw_store_f(self, struct, offset, newvalue, descr):
        ll_p = rffi.cast(rffi.CCHARP, struct)
        ll_p = rffi.cast(rffi.CArrayPtr(longlong.FLOATSTORAGE),
                         rffi.ptradd(ll_p, offset))
        ll_p[0] = newvalue

    def bh_raw_store(self, struct, offset, newvalue, descr):
        if descr.A.OF == lltype.Float:
            self.bh_raw_store_f(struct, offset, newvalue, descr)
        else:
            self.bh_raw_store_i(struct, offset, newvalue, descr)

    def bh_newstr(self, length):
        return lltype.cast_opaque_ptr(llmemory.GCREF,
                                      lltype.malloc(rstr.STR, length,
                                                    zero=True))

    def bh_strlen(self, s):
        return s._obj.container.chars.getlength()

    def bh_strgetitem(self, s, item):
        return ord(s._obj.container.chars.getitem(item))

    def bh_strsetitem(self, s, item, v):
        s._obj.container.chars.setitem(item, chr(v))

    def bh_copystrcontent(self, src, dst, srcstart, dststart, length):
        src = lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR), src)
        dst = lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR), dst)
        assert 0 <= srcstart <= srcstart + length <= len(src.chars)
        assert 0 <= dststart <= dststart + length <= len(dst.chars)
        rstr.copy_string_contents(src, dst, srcstart, dststart, length)

    def bh_newunicode(self, length):
        return lltype.cast_opaque_ptr(llmemory.GCREF,
                                      lltype.malloc(rstr.UNICODE, length,
                                                    zero=True))

    def bh_unicodelen(self, string):
        return string._obj.container.chars.getlength()

    def bh_unicodegetitem(self, string, index):
        return ord(string._obj.container.chars.getitem(index))

    def bh_unicodesetitem(self, string, index, newvalue):
        string._obj.container.chars.setitem(index, unichr(newvalue))

    def bh_copyunicodecontent(self, src, dst, srcstart, dststart, length):
        src = lltype.cast_opaque_ptr(lltype.Ptr(rstr.UNICODE), src)
        dst = lltype.cast_opaque_ptr(lltype.Ptr(rstr.UNICODE), dst)
        assert 0 <= srcstart <= srcstart + length <= len(src.chars)
        assert 0 <= dststart <= dststart + length <= len(dst.chars)
        rstr.copy_unicode_contents(src, dst, srcstart, dststart, length)

    def bh_new(self, sizedescr):
        return lltype.cast_opaque_ptr(llmemory.GCREF,
                                      lltype.malloc(sizedescr.S, zero=True))

    def bh_new_with_vtable(self, vtable, descr):
        result = lltype.malloc(descr.S, zero=True)
        result_as_objptr = lltype.cast_pointer(rclass.OBJECTPTR, result)
        result_as_objptr.typeptr = support.cast_from_int(rclass.CLASSTYPE,
                                                         vtable)
        return lltype.cast_opaque_ptr(llmemory.GCREF, result)

    def bh_new_array(self, length, arraydescr):
        array = lltype.malloc(arraydescr.A, length, zero=True)
        return lltype.cast_opaque_ptr(llmemory.GCREF, array)

    def bh_classof(self, struct):
        struct = lltype.cast_opaque_ptr(rclass.OBJECTPTR, struct)
        result_adr = llmemory.cast_ptr_to_adr(struct.typeptr)
        return heaptracker.adr2int(result_adr)

    def bh_read_timestamp(self):
        return read_timestamp()

    def bh_new_raw_buffer(self, size):
        return lltype.malloc(rffi.CCHARP.TO, size, flavor='raw')

    def store_fail_descr(self, deadframe, descr):
        pass # I *think*



class LLDeadFrame(object):
    _TYPE = llmemory.GCREF

    def __init__(self, latest_descr, values,
                 last_exception=None, saved_data=None):
        self._latest_descr = latest_descr
        self._values = values
        self._last_exception = last_exception
        self._saved_data = saved_data


class LLFrame(object):
    _TYPE = llmemory.GCREF

    forced_deadframe = None
    overflow_flag = False
    last_exception = None
    force_guard_op = None

    def __init__(self, cpu, argboxes, args):
        self.env = {}
        self.cpu = cpu
        assert len(argboxes) == len(args)
        for box, arg in zip(argboxes, args):
            self.setenv(box, arg)

    def __eq__(self, other):
        # this is here to avoid crashes in 'token == TOKEN_TRACING_RESCALL'
        from rpython.jit.metainterp.virtualizable import TOKEN_NONE
        from rpython.jit.metainterp.virtualizable import TOKEN_TRACING_RESCALL
        if isinstance(other, LLFrame):
            return self is other
        if other == TOKEN_NONE or other == TOKEN_TRACING_RESCALL:
            return False
        assert 0

    def __ne__(self, other):
        return not (self == other)

    def _identityhash(self):
        return hash(self)

    def setenv(self, box, arg):
        if box.type == INT:
            # typecheck the result
            if isinstance(arg, bool):
                arg = int(arg)
            assert lltype.typeOf(arg) == lltype.Signed
        elif box.type == REF:
            assert lltype.typeOf(arg) == llmemory.GCREF
        elif box.type == FLOAT:
            assert lltype.typeOf(arg) == longlong.FLOATSTORAGE
        else:
            raise AssertionError(box)
        #
        self.env[box] = arg

    def lookup(self, arg):
        if isinstance(arg, Const):
            return arg.value
        return self.env[arg]

    def execute(self, lltrace):
        self.lltrace = lltrace
        del lltrace
        i = 0
        while True:
            assert not self.lltrace.has_been_freed
            op = self.lltrace.operations[i]
            args = [self.lookup(arg) for arg in op.getarglist()]
            self.current_op = op # for label
            self.current_index = i
            execute = getattr(self, 'execute_' + op.getopname())
            try:
                resval = execute(_getdescr(op), *args)
            except Jump, j:
                self.lltrace, i = j.jump_target
                if i >= 0:
                    label_op = self.lltrace.operations[i]
                    i += 1
                    targetargs = label_op.getarglist()
                else:
                    targetargs = self.lltrace.inputargs
                    i = 0
                self.do_renaming(targetargs, j.args)
                continue
            if op.result is not None:
                self.setenv(op.result, resval)
            else:
                assert resval is None
            i += 1

    def do_renaming(self, newargs, newvalues):
        assert len(newargs) == len(newvalues)
        self.env = {}
        self.framecontent = {}
        for new, newvalue in zip(newargs, newvalues):
            self.setenv(new, newvalue)

    # -----------------------------------------------------

    def fail_guard(self, descr, saved_data=None):
        values = []
        for box in self.current_op.getfailargs():
            if box is not None:
                value = self.env[box]
            else:
                value = None
            values.append(value)
        if hasattr(descr, '_llgraph_bridge'):
            target = (descr._llgraph_bridge, -1)
            values = [value for value in values if value is not None]
            raise Jump(target, values)
        else:
            raise ExecutionFinished(LLDeadFrame(descr, values,
                                                self.last_exception,
                                                saved_data))

    def execute_force_spill(self, _, arg):
        pass

    def execute_finish(self, descr, *args):
        raise ExecutionFinished(LLDeadFrame(descr, args))

    def execute_label(self, descr, *args):
        argboxes = self.current_op.getarglist()
        self.do_renaming(argboxes, args)

    def execute_guard_true(self, descr, arg):
        if not arg:
            self.fail_guard(descr)

    def execute_guard_false(self, descr, arg):
        if arg:
            self.fail_guard(descr)

    def execute_guard_value(self, descr, arg1, arg2):
        if arg1 != arg2:
            self.fail_guard(descr)

    def execute_guard_nonnull(self, descr, arg):
        if not arg:
            self.fail_guard(descr)

    def execute_guard_isnull(self, descr, arg):
        if arg:
            self.fail_guard(descr)

    def execute_guard_class(self, descr, arg, klass):
        value = lltype.cast_opaque_ptr(rclass.OBJECTPTR, arg)
        expected_class = llmemory.cast_adr_to_ptr(
            llmemory.cast_int_to_adr(klass),
            rclass.CLASSTYPE)
        if value.typeptr != expected_class:
            self.fail_guard(descr)

    def execute_guard_nonnull_class(self, descr, arg, klass):
        self.execute_guard_nonnull(descr, arg)
        self.execute_guard_class(descr, arg, klass)

    def execute_guard_no_exception(self, descr):
        if self.last_exception is not None:
            self.fail_guard(descr)

    def execute_guard_exception(self, descr, excklass):
        lle = self.last_exception
        if lle is None:
            gotklass = lltype.nullptr(rclass.CLASSTYPE.TO)
        else:
            gotklass = lle.args[0]
        excklass = llmemory.cast_adr_to_ptr(
            llmemory.cast_int_to_adr(excklass),
            rclass.CLASSTYPE)
        if gotklass != excklass:
            self.fail_guard(descr)
        #
        res = lle.args[1]
        self.last_exception = None
        return support.cast_to_ptr(res)

    def execute_guard_not_forced(self, descr):
        if self.forced_deadframe is not None:
            saved_data = self.forced_deadframe._saved_data
            self.fail_guard(descr, saved_data)
        self.force_guard_op = self.current_op
    execute_guard_not_forced_2 = execute_guard_not_forced

    def execute_guard_not_invalidated(self, descr):
        if self.lltrace.invalid:
            self.fail_guard(descr)

    def execute_int_add_ovf(self, _, x, y):
        try:
            z = ovfcheck(x + y)
        except OverflowError:
            ovf = True
            z = 0
        else:
            ovf = False
        self.overflow_flag = ovf
        return z

    def execute_int_sub_ovf(self, _, x, y):
        try:
            z = ovfcheck(x - y)
        except OverflowError:
            ovf = True
            z = 0
        else:
            ovf = False
        self.overflow_flag = ovf
        return z

    def execute_int_mul_ovf(self, _, x, y):
        try:
            z = ovfcheck(x * y)
        except OverflowError:
            ovf = True
            z = 0
        else:
            ovf = False
        self.overflow_flag = ovf
        return z

    def execute_guard_no_overflow(self, descr):
        if self.overflow_flag:
            self.fail_guard(descr)

    def execute_guard_overflow(self, descr):
        if not self.overflow_flag:
            self.fail_guard(descr)

    def execute_jump(self, descr, *args):
        raise Jump(descr._llgraph_target, args)

    def _do_math_sqrt(self, value):
        import math
        y = support.cast_from_floatstorage(lltype.Float, value)
        x = math.sqrt(y)
        return support.cast_to_floatstorage(x)

    def execute_cond_call(self, calldescr, cond, func, *args):
        if not cond:
            return
        # cond_call can't have a return value
        self.execute_call(calldescr, func, *args)

    def execute_call(self, calldescr, func, *args):
        effectinfo = calldescr.get_extra_info()
        if effectinfo is not None and hasattr(effectinfo, 'oopspecindex'):
            oopspecindex = effectinfo.oopspecindex
            if oopspecindex == EffectInfo.OS_MATH_SQRT:
                return self._do_math_sqrt(args[0])
        TP = llmemory.cast_int_to_adr(func).ptr._obj._TYPE
        call_args = support.cast_call_args_in_order(TP.ARGS, args)
        try:
            res = self.cpu.maybe_on_top_of_llinterp(func, call_args, TP.RESULT)
            self.last_exception = None
        except LLException, lle:
            self.last_exception = lle
            res = _example_res[getkind(TP.RESULT)[0]]
        return res

    def execute_call_may_force(self, calldescr, func, *args):
        call_op = self.lltrace.operations[self.current_index]
        guard_op = self.lltrace.operations[self.current_index + 1]
        assert guard_op.getopnum() == rop.GUARD_NOT_FORCED
        self.force_guard_op = guard_op
        res = self.execute_call(calldescr, func, *args)
        del self.force_guard_op
        return res

    def execute_call_release_gil(self, descr, func, *args):
        if hasattr(descr, '_original_func_'):
            func = descr._original_func_     # see pyjitpl.py
            # we want to call the function that does the aroundstate
            # manipulation here (as a hack, instead of really doing
            # the aroundstate manipulation ourselves)
            return self.execute_call_may_force(descr, func, *args)
        guard_op = self.lltrace.operations[self.current_index + 1]
        assert guard_op.getopnum() == rop.GUARD_NOT_FORCED
        self.force_guard_op = guard_op
        call_args = support.cast_call_args_in_order(descr.ARGS, args)
        #
        func_adr = llmemory.cast_int_to_adr(func)
        if hasattr(func_adr.ptr._obj, '_callable'):
            # this is needed e.g. by test_fficall.test_guard_not_forced_fails,
            # because to actually force the virtualref we need to llinterp the
            # graph, not to directly execute the python function
            result = self.cpu.maybe_on_top_of_llinterp(func, call_args, descr.RESULT)
        else:
            FUNC = lltype.FuncType(descr.ARGS, descr.RESULT)
            func_to_call = rffi.cast(lltype.Ptr(FUNC), func)
            result = func_to_call(*call_args)
        del self.force_guard_op
        return support.cast_result(descr.RESULT, result)

    def execute_call_assembler(self, descr, *args):
        # XXX simplify the following a bit
        #
        # pframe = CALL_ASSEMBLER(args..., descr=looptoken)
        # ==>
        #     pframe = CALL looptoken.loopaddr(*args)
        #     JUMP_IF_FAST_PATH @fastpath
        #     res = CALL assembler_call_helper(pframe)
        #     jmp @done
        #   @fastpath:
        #     res = GETFIELD(pframe, 'result')
        #   @done:
        #
        call_op = self.lltrace.operations[self.current_index]
        guard_op = self.lltrace.operations[self.current_index + 1]
        assert guard_op.getopnum() == rop.GUARD_NOT_FORCED
        self.force_guard_op = guard_op
        pframe = self.cpu._execute_token(descr, *args)
        del self.force_guard_op
        #
        jd = descr.outermost_jitdriver_sd
        assert jd is not None, ("call_assembler(): the loop_token needs "
                                "to have 'outermost_jitdriver_sd'")
        if jd.index_of_virtualizable != -1:
            vable = args[jd.index_of_virtualizable]
        else:
            vable = lltype.nullptr(llmemory.GCREF.TO)
        #
        # Emulate the fast path
        #
        faildescr = self.cpu.get_latest_descr(pframe)
        if faildescr == self.cpu.done_with_this_frame_descr_int:
            return self.cpu.get_int_value(pframe, 0)
        elif faildescr == self.cpu.done_with_this_frame_descr_ref:
            return self.cpu.get_ref_value(pframe, 0)
        elif faildescr == self.cpu.done_with_this_frame_descr_float:
            return self.cpu.get_float_value(pframe, 0)
        elif faildescr == self.cpu.done_with_this_frame_descr_void:
            return None

        assembler_helper_ptr = jd.assembler_helper_adr.ptr  # fish
        try:
            result = assembler_helper_ptr(pframe, vable)
        except LLException, lle:
            assert self.last_exception is None, "exception left behind"
            self.last_exception = lle
            # fish op
            op = self.current_op
            return op.result and op.result.value
        if isinstance(result, float):
            result = support.cast_to_floatstorage(result)
        return result

    def execute_same_as(self, _, x):
        return x

    def execute_debug_merge_point(self, descr, *args):
        from rpython.jit.metainterp.warmspot import get_stats
        try:
            stats = get_stats()
        except AttributeError:
            pass
        else:
            stats.add_merge_point_location(args[1:])

    def execute_new_with_vtable(self, _, vtable):
        descr = heaptracker.vtable2descr(self.cpu, vtable)
        return self.cpu.bh_new_with_vtable(vtable, descr)

    def execute_force_token(self, _):
        return self

    def execute_cond_call_gc_wb(self, descr, a):
        py.test.skip("cond_call_gc_wb not supported")

    def execute_cond_call_gc_wb_array(self, descr, a, b):
        py.test.skip("cond_call_gc_wb_array not supported")

    def execute_keepalive(self, descr, x):
        pass


def _getdescr(op):
    d = op.getdescr()
    if d is not None and isinstance(d, WeakrefDescr):
        d = d.realdescrref()
        assert d is not None, "the descr disappeared: %r" % (op,)
    return d

def _setup():
    def _make_impl_from_blackhole_interp(opname):
        from rpython.jit.metainterp.blackhole import BlackholeInterpreter
        name = 'bhimpl_' + opname.lower()
        try:
            func = BlackholeInterpreter.__dict__[name]
        except KeyError:
            return
        for argtype in func.argtypes:
            if argtype not in ('i', 'r', 'f'):
                return
        #
        def _op_default_implementation(self, descr, *args):
            # for all operations implemented in the blackhole interpreter
            return func(*args)
        #
        _op_default_implementation.func_name = 'execute_' + opname
        return _op_default_implementation

    def _new_execute(opname):
        def execute(self, descr, *args):
            if descr is not None:
                new_args = args + (descr,)
            else:
                new_args = args
            return getattr(self.cpu, 'bh_' + opname)(*new_args)
        execute.func_name = 'execute_' + opname
        return execute

    for k, v in rop.__dict__.iteritems():
        if not k.startswith("_"):
            fname = 'execute_' + k.lower()
            if not hasattr(LLFrame, fname):
                func = _make_impl_from_blackhole_interp(k)
                if func is None:
                    func = _new_execute(k.lower())
                setattr(LLFrame, fname, func)

_setup()
