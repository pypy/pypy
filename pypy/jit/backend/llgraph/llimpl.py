"""
The non-RPythonic part of the llgraph backend.
This contains all the code that is directly run
when executing on top of the llinterpreter.
"""

import sys
from pypy.objspace.flow.model import Variable, Constant
from pypy.annotation import model as annmodel
from pypy.jit.metainterp.history import (ConstInt, ConstPtr, ConstAddr, ConstObj,
                                         BoxInt, BoxPtr, BoxObj)
from pypy.rpython.lltypesystem import lltype, llmemory, rclass, rstr
from pypy.rpython.lltypesystem import lloperation
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.module.support import LLSupport, OOSupport
from pypy.rpython.llinterp import LLException
from pypy.rpython.extregistry import ExtRegistryEntry

from pypy.jit.metainterp import heaptracker, resoperation, executor
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.backend.llgraph import symbolic

from pypy.rlib.objectmodel import ComputedIntSymbolic
from pypy.rlib.rarithmetic import r_uint, intmask

import py
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer('runner')
py.log.setconsumer('runner', ansi_log)


def _from_opaque(opq):
    return opq._obj.externalobj

_TO_OPAQUE = {}

def _to_opaque(value):
    return lltype.opaqueptr(_TO_OPAQUE[value.__class__], 'opaque',
                            externalobj=value)

def from_opaque_string(s):
    if isinstance(s, str):
        return s
    elif isinstance(s, ootype._string):
        return OOSupport.from_rstr(s)
    else:
        return LLSupport.from_rstr(s)

# a list of argtypes of all operations - couldn't find any and it's
# very useful
TYPES = {
    'int_add'         : (('int', 'int'), 'int'),
    'int_sub'         : (('int', 'int'), 'int'),
    'int_mul'         : (('int', 'int'), 'int'),
    'int_floordiv'    : (('int', 'int'), 'int'),
    'int_mod'         : (('int', 'int'), 'int'),
    'int_and'         : (('int', 'int'), 'int'),
    'int_or'          : (('int', 'int'), 'int'),
    'int_xor'         : (('int', 'int'), 'int'),
    'int_lshift'      : (('int', 'int'), 'int'),
    'int_rshift'      : (('int', 'int'), 'int'),
    'int_lt'          : (('int', 'int'), 'bool'),
    'int_gt'          : (('int', 'int'), 'bool'),
    'int_ge'          : (('int', 'int'), 'bool'),
    'int_le'          : (('int', 'int'), 'bool'),
    'int_eq'          : (('int', 'int'), 'bool'),
    'int_ne'          : (('int', 'int'), 'bool'),
    'int_is_true'     : (('int',), 'bool'),
    'int_neg'         : (('int',), 'int'),
    'int_invert'      : (('int',), 'int'),
    'int_add_ovf'     : (('int', 'int'), 'int'),
    'int_sub_ovf'     : (('int', 'int'), 'int'),
    'int_mul_ovf'     : (('int', 'int'), 'int'),
    'int_neg_ovf'     : (('int',), 'int'),
    'int_lshift_ovf'  : (('int', 'int'), 'int'),
    'bool_not'        : (('bool',), 'bool'),
    'uint_add'        : (('int', 'int'), 'int'),
    'uint_sub'        : (('int', 'int'), 'int'),
    'uint_mul'        : (('int', 'int'), 'int'),
    'uint_lt'         : (('int', 'int'), 'bool'),
    'uint_le'         : (('int', 'int'), 'bool'),
    'uint_eq'         : (('int', 'int'), 'bool'),
    'uint_ne'         : (('int', 'int'), 'bool'),
    'uint_gt'         : (('int', 'int'), 'bool'),
    'uint_ge'         : (('int', 'int'), 'bool'),
    'uint_xor'        : (('int', 'int'), 'int'),
    'uint_rshift'     : (('int', 'int'), 'int'),
    'new_with_vtable' : (('ptr',), 'ptr'),
    'new'             : ((), 'ptr'),
    'new_array'       : (('int',), 'ptr'),
    'oononnull'       : (('ptr',), 'bool'),
    'ooisnull'        : (('ptr',), 'bool'),
    'oois'            : (('ptr', 'ptr'), 'bool'),
    'ooisnot'         : (('ptr', 'ptr'), 'bool'),
    'instanceof'      : (('ptr',), 'bool'),
    'setfield_gc'     : (('ptr', 'intorptr'), None),
    'getfield_gc'     : (('ptr',), 'intorptr'),
    'getfield_gc_pure': (('ptr',), 'intorptr'),
    'setfield_raw'    : (('ptr', 'intorptr'), None),
    'getfield_raw'    : (('ptr',), 'intorptr'),
    'getfield_raw_pure': (('ptr',), 'intorptr'),
    'setarrayitem_gc' : (('ptr', 'int', 'intorptr'), None),
    'getarrayitem_gc' : (('ptr', 'int'), 'intorptr'),
    'getarrayitem_gc_pure' : (('ptr', 'int'), 'intorptr'),
    'arraylen_gc'     : (('ptr',), 'int'),
    'call'            : (('ptr', 'varargs'), 'intorptr'),
    'call_pure'       : (('ptr', 'varargs'), 'intorptr'),
    'oosend'          : (('varargs',), 'intorptr'),
    'oosend_pure'     : (('varargs',), 'intorptr'),
    'guard_true'      : (('bool',), None),
    'guard_false'     : (('bool',), None),
    'guard_value'     : (('int', 'int'), None),
    'guard_value_inverse'  : (('int', 'int'), None),
    'guard_class'     : (('ptr', 'ptr'), None),
    'guard_no_exception'   : ((), None),
    'guard_exception'      : (('ptr',), 'ptr'),
    'guard_nonvirtualized' : (('ptr', 'ptr'), None),
    'newstr'          : (('int',), 'ptr'),
    'strlen'          : (('ptr',), 'int'),
    'strgetitem'      : (('ptr', 'int'), 'int'),
    'strsetitem'      : (('ptr', 'int', 'int'), None),
    'newunicode'      : (('int',), 'ptr'),
    'unicodelen'      : (('ptr',), 'int'),
    'unicodegetitem'  : (('ptr', 'int'), 'int'),
    'unicodesetitem'  : (('ptr', 'int', 'int'), 'int'),
    'cast_ptr_to_int' : (('ptr',), 'int'),
    'cast_int_to_ptr' : (('int',), 'ptr'),
    #'getitem'         : (('void', 'ptr', 'int'), 'int'),
    #'setitem'         : (('void', 'ptr', 'int', 'int'), None),
    #'newlist'         : (('void', 'varargs'), 'ptr'),
    #'append'          : (('void', 'ptr', 'int'), None),
    #'insert'          : (('void', 'ptr', 'int', 'int'), None),
    #'pop'             : (('void', 'ptr',), 'int'),
    #'len'             : (('void', 'ptr',), 'int'),
    #'listnonzero'     : (('void', 'ptr',), 'int'),
}

# ____________________________________________________________

class CompiledLoop(object):
    def __init__(self):
        self.inputargs = []
        self.operations = []

    def __repr__(self):
        lines = []
        self.as_text(lines, 1)
        return 'CompiledLoop:\n%s' % '\n'.join(lines)

    def as_text(self, lines, indent):
        for op in self.operations:
            lines.append('\t'*indent + repr(op))
            if op.is_guard():
                op.subloop.as_text(lines, indent+1)

class Operation(object):
    def __init__(self, opnum):
        self.opnum = opnum
        self.args = []
        self.result = None
        self.descr = None
        self.livevars = []   # for guards only

    def __repr__(self):
        if self.result is not None:
            sres = repr0(self.result) + ' = '
        else:
            sres = ''
        return '{%s%s(%s)}' % (sres, self.getopname(),
                               ', '.join(map(repr0, self.args)))

    def getopname(self):
        try:
            return resoperation.opname[self.opnum]
        except KeyError:
            return '<%d>' % self.opnum

    def is_guard(self):
        return rop._GUARD_FIRST <= self.opnum <= rop._GUARD_LAST

    def is_final(self):
        return rop._FINAL_FIRST <= self.opnum <= rop._FINAL_LAST

def repr0(x):
    if isinstance(x, list):
        return '[' + ', '.join(repr0(y) for y in x) + ']'
    elif isinstance(x, Constant):
        return '(' + repr0(x.value) + ')'
    elif isinstance(x, lltype._ptr):
        x = llmemory.cast_ptr_to_adr(x)
        if x.ptr:
            try:
                container = x.ptr._obj._normalizedcontainer()
                return '* %s' % (container._TYPE._short_name(),)
            except AttributeError:
                return repr(x)
        else:
            return 'NULL'
    else:
        return repr(x)

def repr_list(lst, types, memocast):
    res_l = []
    if types and types[-1] == 'varargs':
        types = types[:-1] + ('int',) * (len(lst) - len(types) + 1)
    assert len(types) == len(lst)
    for elem, tp in zip(lst, types):
        if isinstance(elem, Constant):
            res_l.append('(%s)' % repr1(elem, tp, memocast))
        else:
            res_l.append(repr1(elem, tp, memocast))
    return '[%s]' % (', '.join(res_l))

def repr1(x, tp, memocast):
    if tp == "intorptr":
        TYPE = lltype.typeOf(x)
        if isinstance(TYPE, lltype.Ptr) and TYPE.TO._gckind == 'gc':
            tp = "ptr"
        else:
            tp = "int"
    if tp == 'int':
        return str(x)
    elif tp == 'void':
        return '---'
    elif tp == 'ptr':
        if not x:
            return '(* None)'
        if isinstance(x, int):
            # XXX normalize?
            ptr = str(cast_int_to_adr(memocast, x))
        elif isinstance(ootype.typeOf(x), ootype.OOType):
            return repr(x)
        else:
            if getattr(x, '_fake', None):
                return repr(x)
            if lltype.typeOf(x) == llmemory.GCREF:
                TP = lltype.Ptr(lltype.typeOf(x._obj.container))
                ptr = lltype.cast_opaque_ptr(TP, x)
            else:
                ptr = x
        try:
            container = ptr._obj._normalizedcontainer()
            return '(* %s)' % (container._TYPE._short_name(),)
        except AttributeError:
            return '(%r)' % (ptr,)
    elif tp == 'bool':
        assert x == 0 or x == 1
        return str(bool(x))
    #elif tp == 'fieldname':
    #    return str(symbolic.TokenToField[x...][1])
    else:
        raise NotImplementedError("tp = %s" % tp)

_variables = []

def compile_start():
    del _variables[:]
    return _to_opaque(CompiledLoop())

def compile_start_int_var(loop):
    loop = _from_opaque(loop)
    assert not loop.operations
    v = Variable()
    v.concretetype = lltype.Signed
    loop.inputargs.append(v)
    r = len(_variables)
    _variables.append(v)
    return r

def compile_start_ptr_var(loop):
    loop = _from_opaque(loop)
    assert not loop.operations
    v = Variable()
    v.concretetype = llmemory.GCREF
    loop.inputargs.append(v)
    r = len(_variables)
    _variables.append(v)
    return r

def compile_start_obj_var(loop):
    loop = _from_opaque(loop)
    assert not loop.operations
    v = Variable()
    v.concretetype = ootype.Object
    loop.inputargs.append(v)
    r = len(_variables)
    _variables.append(v)
    return r

def compile_add(loop, opnum):
    loop = _from_opaque(loop)
    loop.operations.append(Operation(opnum))

def compile_add_descr(loop, ofs, type):
    from pypy.jit.backend.llgraph.runner import Descr
    loop = _from_opaque(loop)
    op = loop.operations[-1]
    assert isinstance(type, str) and len(type) == 1
    op.descr = Descr(ofs, type)

def compile_add_var(loop, intvar):
    loop = _from_opaque(loop)
    op = loop.operations[-1]
    op.args.append(_variables[intvar])

def compile_add_int_const(loop, value):
    loop = _from_opaque(loop)
    const = Constant(value)
    const.concretetype = lltype.Signed
    op = loop.operations[-1]
    op.args.append(const)

def compile_add_ptr_const(loop, value, TYPE=llmemory.GCREF):
    loop = _from_opaque(loop)
    const = Constant(value)
    const.concretetype = TYPE
    op = loop.operations[-1]
    op.args.append(const)

def compile_add_int_result(loop):
    loop = _from_opaque(loop)
    v = Variable()
    v.concretetype = lltype.Signed
    op = loop.operations[-1]
    op.result = v
    r = len(_variables)
    _variables.append(v)
    return r

def compile_add_ptr_result(loop, TYPE=llmemory.GCREF):
    loop = _from_opaque(loop)
    v = Variable()
    v.concretetype = TYPE
    op = loop.operations[-1]
    op.result = v
    r = len(_variables)
    _variables.append(v)
    return r

def compile_add_jump_target(loop, loop_target):
    loop = _from_opaque(loop)
    loop_target = _from_opaque(loop_target)
    op = loop.operations[-1]
    op.jump_target = loop_target
    assert op.opnum == rop.JUMP
    assert len(op.args) == len(loop_target.inputargs)
    if loop_target == loop:
        log.info("compiling new loop")
    else:
        log.info("compiling new bridge")

def compile_add_fail(loop, fail_index):
    loop = _from_opaque(loop)
    op = loop.operations[-1]
    assert op.opnum == rop.FAIL
    op.fail_index = fail_index

def compile_suboperations(loop):
    loop = _from_opaque(loop)
    op = loop.operations[-1]
    assert op.is_guard()
    op.subloop = CompiledLoop()
    return _to_opaque(op.subloop)

def compile_redirect_code(old_loop, new_loop):
    old_loop = _from_opaque(old_loop)
    new_loop = _from_opaque(new_loop)
    # we patch the old_loop so that it starts with a JUMP to the new_loop
    # (but only if we can reasonably -- if new arguments grew, it is not)
    if len(old_loop.inputargs) == len(new_loop.inputargs):
        op = Operation(rop.JUMP)
        op.args = old_loop.inputargs
        op.jump_target = new_loop
        old_loop.operations[0] = op

# ------------------------------

class Frame(object):
    OPHANDLERS = [None] * (rop._LAST+1)

    def __init__(self, memocast):
        self.verbose = False
        self.memocast = memocast

    def getenv(self, v):
        if isinstance(v, Constant):
            return v.value
        else:
            return self.env[v]

    def execute(self):
        """Execute all operations in a loop,
        possibly following to other loops as well.
        """
        global _last_exception
        assert _last_exception is None, "exception left behind"
        verbose = True
        operations = self.loop.operations
        opindex = 0
        while True:
            op = operations[opindex]
            args = [self.getenv(v) for v in op.args]
            if not op.is_final():
                try:
                    result = self.execute_operation(op.opnum, args, op.descr,
                                                    verbose)
                except GuardFailed:
                    assert op.is_guard()
                    _stats.exec_conditional_jumps += 1
                    operations = op.subloop.operations
                    opindex = 0
                    continue
                #verbose = self.verbose
                assert (result is None) == (op.result is None)
                if op.result is not None:
                    RESTYPE = op.result.concretetype
                    if RESTYPE is lltype.Signed:
                        x = self.as_int(result)
                    elif RESTYPE is llmemory.GCREF:
                        x = self.as_ptr(result)
                    elif RESTYPE is ootype.Object:
                        x = self.as_object(result)
                    else:
                        raise Exception("op.result.concretetype is %r"
                                        % (RESTYPE,))
                    self.env[op.result] = x
                opindex += 1
                continue
            if op.opnum == rop.JUMP:
                assert len(op.jump_target.inputargs) == len(args)
                self.env = dict(zip(op.jump_target.inputargs, args))
                operations = op.jump_target.operations
                opindex = 0
                _stats.exec_jumps += 1
            elif op.opnum == rop.FAIL:
                if self.verbose:
                    log.trace('failed: %s' % (
                        ', '.join(map(str, args)),))
                self.fail_args = args
                return op.fail_index
            else:
                assert 0, "unknown final operation %d" % (op.opnum,)

    def execute_operation(self, opnum, values, descr, verbose):
        """Execute a single operation.
        """
        ophandler = self.OPHANDLERS[opnum]
        if ophandler is None:
            self._define_impl(opnum)
            ophandler = self.OPHANDLERS[opnum]
            assert ophandler is not None, "missing impl for op %d" % opnum
        opname = resoperation.opname[opnum].lower()
        exec_counters = _stats.exec_counters
        exec_counters[opname] = exec_counters.get(opname, 0) + 1
        for i in range(len(values)):
            if isinstance(values[i], ComputedIntSymbolic):
                values[i] = values[i].compute_fn()
        res = NotImplemented
        try:
            res = ophandler(self, descr, *values)
        finally:
            if verbose:
                argtypes, restype = TYPES[opname]
                if res is None:
                    resdata = ''
                elif res is NotImplemented:
                    resdata = '*fail*'
                else:
                    resdata = '-> ' + repr1(res, restype, self.memocast)
                # fish the types
                #log.cpu('\t%s %s %s' % (opname, repr_list(values, argtypes,
                #                                          self.memocast),
                #                        resdata))
        return res

    def as_int(self, x):
        return cast_to_int(x, self.memocast)

    def as_ptr(self, x):
        return cast_to_ptr(x)

    def as_object(self, x):
        return ootype.cast_to_object(x)

    def log_progress(self):
        count = sum(_stats.exec_counters.values())
        count_jumps = _stats.exec_jumps
        log.trace('ran %d operations, %d jumps' % (count, count_jumps))

    # ----------

    @classmethod
    def _define_impl(cls, opnum):
        opname = resoperation.opname[opnum]
        try:
            op = getattr(cls, 'op_' + opname.lower())   # op_guard_true etc.
        except AttributeError:
            name = 'do_' + opname.lower()
            try:
                impl = globals()[name]                    # do_arraylen_gc etc.
                def op(self, descr, *args):
                    return impl(descr, *args)
                #
            except KeyError:
                from pypy.jit.backend.llgraph import llimpl
                impl = getattr(executor, name)            # do_int_add etc.
                def _op_default_implementation(self, descr, *args):
                    # for all operations implemented in execute.py
                    boxedargs = []
                    for x in args:
                        if type(x) is int:
                            boxedargs.append(BoxInt(x))
                        elif isinstance(ootype.typeOf(x), ootype.OOType):
                            boxedargs.append(BoxObj(ootype.cast_to_object(x)))
                        else:
                            boxedargs.append(BoxPtr(x))
                    # xxx this passes the 'llimpl' module as the CPU argument
                    resbox = impl(llimpl, boxedargs)
                    return resbox.value
                op = _op_default_implementation
                #
        cls.OPHANDLERS[opnum] = op

    def op_guard_true(self, _, value):
        if not value:
            raise GuardFailed

    def op_guard_false(self, _, value):
        if value:
            raise GuardFailed

    def op_guard_class(self, _, value, expected_class):
        value = lltype.cast_opaque_ptr(rclass.OBJECTPTR, value)
        expected_class = llmemory.cast_adr_to_ptr(
            cast_int_to_adr(self.memocast, expected_class),
            rclass.CLASSTYPE)
        if value.typeptr != expected_class:
            raise GuardFailed

    def op_guard_class_inverse(self, _, value, expected_class):
        value = lltype.cast_opaque_ptr(rclass.OBJECTPTR, value)
        expected_class = llmemory.cast_adr_to_ptr(
            cast_int_to_adr(self.memocast, expected_class),
            rclass.CLASSTYPE)
        if value.typeptr == expected_class:
            raise GuardFailed

    def op_guard_value(self, _, value, expected_value):
        if value != expected_value:
            raise GuardFailed

    def op_guard_value_inverse(self, _, value, expected_value):
        if value == expected_value:
            raise GuardFailed

    def op_guard_nonvirtualized(self, for_accessing_field,
                                value, expected_class=None):
        # XXX
        # We completely ignore guard_nonvirtualized
        # right now, nobody can devirtualize a virtualizable anyway
        # and we abuse guard_nonvirtualized for propagating properties
        return
        if expected_class is not None:
            self.op_guard_class(-1, value, expected_class)
        if heaptracker.cast_vable(value).vable_rti:
            raise GuardFailed    # some other code is already in control

    def op_guard_no_exception(self, _):
        if _last_exception:
            raise GuardFailed

    def op_guard_no_exception_inverse(self, _):
        if _last_exception is None:
            raise GuardFailed

    def _check_exception(self, expected_exception):
        global _last_exception
        expected_exception = self._cast_exception(expected_exception)
        assert expected_exception
        exc = _last_exception
        if exc:
            got = exc.args[0]
            if not self._issubclass(got, expected_exception):
                return False
            return True
        else:
            return False

    def _cast_exception(self, exception):
        return llmemory.cast_adr_to_ptr(
            cast_int_to_adr(self.memocast, exception),
            rclass.CLASSTYPE)

    def _issubclass(self, cls1, cls2):
        return rclass.ll_issubclass(cls1, cls2)

    def op_guard_exception(self, _, expected_exception):
        global _last_exception
        if not self._check_exception(expected_exception):
            raise GuardFailed
        res = _last_exception[1]
        _last_exception = None
        return res

    def op_guard_exception_inverse(self, _, expected_exception):
        global _last_exception
        if self._check_exception(expected_exception):
            raise GuardFailed
        res = _last_exception[1]
        _last_exception = None
        return res
    
    # ----------
    # delegating to the builtins do_xxx() (done automatically for simple cases)

    def op_getarrayitem_gc(self, arraydescr, array, index):
        if arraydescr.type == 'p':
            return do_getarrayitem_gc_ptr(array, index)
        else:
            return do_getarrayitem_gc_int(array, index, self.memocast)

    op_getarrayitem_gc_pure = op_getarrayitem_gc

    def op_getfield_gc(self, fielddescr, struct):
        if fielddescr.type == 'p':
            return do_getfield_gc_ptr(struct, fielddescr.ofs)
        else:
            return do_getfield_gc_int(struct, fielddescr.ofs, self.memocast)

    op_getfield_gc_pure = op_getfield_gc

    def op_getfield_raw(self, fielddescr, struct):
        if fielddescr.type == 'p':
            return do_getfield_raw_ptr(struct, fielddescr.ofs)
        else:
            return do_getfield_raw_int(struct, fielddescr.ofs, self.memocast)

    def op_new(self, size):
        return do_new(size.ofs)

    def op_new_with_vtable(self, size, vtable):
        result = do_new(size.ofs)
        value = lltype.cast_opaque_ptr(rclass.OBJECTPTR, result)
        value.typeptr = cast_from_int(rclass.CLASSTYPE, vtable, self.memocast)
        return result

    def op_setarrayitem_gc(self, arraydescr, array, index, newvalue):
        if arraydescr.type == 'p':
            do_setarrayitem_gc_ptr(array, index, newvalue)
        else:
            do_setarrayitem_gc_int(array, index, newvalue, self.memocast)

    def op_setfield_gc(self, fielddescr, struct, newvalue):
        if fielddescr.type == 'p':
            do_setfield_gc_ptr(struct, fielddescr.ofs, newvalue)
        else:
            do_setfield_gc_int(struct, fielddescr.ofs, newvalue,
                               self.memocast)

    def op_setfield_raw(self, fielddescr, struct, newvalue):
        if fielddescr.type == 'p':
            do_setfield_raw_ptr(struct, fielddescr.ofs, newvalue)
        else:
            do_setfield_raw_int(struct, fielddescr.ofs, newvalue,
                                self.memocast)

    def op_call(self, calldescr, func, *args):
        _call_args[:] = args
        if calldescr.type == 'v':
            err_result = None
        elif calldescr.type == 'p':
            err_result = lltype.nullptr(llmemory.GCREF.TO)
        else:
            assert calldescr.type == 'i'
            err_result = 0
        return _do_call_common(func, self.memocast, err_result)

    op_call_pure = op_call

    def op_oosend(self, descr, obj, *args):
        raise NotImplementedError("oosend for lltype backend??")

    op_oosend_pure = op_oosend

    def op_new_array(self, arraydescr, count):
        return do_new_array(arraydescr.ofs, count)

    def op_cast_ptr_to_int(self, descr, ptr):
        return cast_to_int(ptr, self.memocast)

    def op_cast_int_to_ptr(self, descr, val):
        return cast_from_int(llmemory.GCREF, val, self.memocast)

    def op_uint_xor(self, descr, arg1, arg2):
        return arg1 ^ arg2


class OOFrame(Frame):

    OPHANDLERS = [None] * (rop._LAST+1)
    
    def op_new_with_vtable(self, typedescr, vtable):
        from pypy.jit.backend.llgraph import runner
        return ootype.cast_to_object(ootype.new(typedescr.TYPE))

    def op_new_array(self, typedescr, count):
        res = ootype.oonewarray(typedescr.ARRAY, count)
        return ootype.cast_to_object(res)

    def op_getfield_gc(self, fielddescr, obj):
        TYPE = fielddescr.TYPE
        fieldname = fielddescr.fieldname
        _, T = TYPE._lookup_field(fieldname)
        obj = ootype.cast_from_object(TYPE, obj)
        res = getattr(obj, fieldname)
        if isinstance(T, ootype.OOType):
            return ootype.cast_to_object(res)
        return res

    op_getfield_gc_pure = op_getfield_gc
    
    def op_setfield_gc(self, fielddescr, obj, newvalue):
        TYPE = fielddescr.TYPE
        fieldname = fielddescr.fieldname
        _, T = TYPE._lookup_field(fieldname)
        obj = ootype.cast_from_object(TYPE, obj)
        if isinstance(ootype.typeOf(newvalue), ootype.OOType):
            newvalue = ootype.cast_from_object(T, newvalue)
        setattr(obj, fieldname, newvalue)

    def op_getarrayitem_gc(self, typedescr, obj, index):
        array = ootype.cast_from_object(typedescr.ARRAY, obj)
        res = array.ll_getitem_fast(index)
        if isinstance(typedescr.TYPE, ootype.OOType):
            return ootype.cast_to_object(res)
        return res

    op_getarrayitem_gc_pure = op_getarrayitem_gc

    def op_setarrayitem_gc(self, typedescr, obj, index, objnewvalue):
        array = ootype.cast_from_object(typedescr.ARRAY, obj)
        #newvalue = ootype.cast_from_object(typedescr.TYPE, objnewvalue)
        array.ll_setitem_fast(index, objnewvalue)

    def op_arraylen_gc(self, typedescr, obj):
        array = ootype.cast_from_object(typedescr.ARRAY, obj)
        return array.ll_length()

    def op_call(self, calldescr, func, *args):
        sm = ootype.cast_from_object(calldescr.FUNC, func)
        newargs = cast_call_args(calldescr.FUNC.ARGS, args, self.memocast)
        res = call_maybe_on_top_of_llinterp(sm, newargs)
        if isinstance(calldescr.FUNC.RESULT, ootype.OOType):
            return ootype.cast_to_object(res)
        return res

    op_call_pure = op_call

    def op_oosend(self, descr, obj, *args):
        METH = descr.METH
        obj = ootype.cast_from_object(descr.SELFTYPE, obj)
        meth = getattr(obj, descr.methname)
        newargs = cast_call_args(METH.ARGS, args, self.memocast)
        res = call_maybe_on_top_of_llinterp(meth, newargs)
        if isinstance(METH.RESULT, ootype.OOType):
            return ootype.cast_to_object(res)
        return res

    op_oosend_pure = op_oosend

    def op_guard_class(self, _, value, expected_class):
        value = ootype.cast_from_object(ootype.ROOT, value)
        expected_class = ootype.cast_from_object(ootype.Class, expected_class)
        if ootype.classof(value) is not expected_class:
            raise GuardFailed

    def op_instanceof(self, typedescr, obj):
        inst = ootype.cast_from_object(ootype.ROOT, obj)
        return ootype.instanceof(inst, typedescr.TYPE)

    def _cast_exception(self, exception):
        return ootype.cast_from_object(ootype.Class, exception)

    def _issubclass(self, cls1, cls2):
        return ootype.subclassof(cls1, cls2)

# ____________________________________________________________

def cast_to_int(x, memocast):
    TP = lltype.typeOf(x)
    if isinstance(TP, lltype.Ptr):
        return cast_adr_to_int(memocast, llmemory.cast_ptr_to_adr(x))
    if TP == llmemory.Address:
        return cast_adr_to_int(memocast, x)
    return lltype.cast_primitive(lltype.Signed, x)

def cast_from_int(TYPE, x, memocast):
    if isinstance(TYPE, lltype.Ptr):
        return llmemory.cast_adr_to_ptr(cast_int_to_adr(memocast, x), TYPE)
    elif TYPE == llmemory.Address:
        return cast_int_to_adr(memocast, x)
    else:
        return lltype.cast_primitive(TYPE, x)

def cast_to_ptr(x):
    assert isinstance(lltype.typeOf(x), lltype.Ptr)
    return lltype.cast_opaque_ptr(llmemory.GCREF, x)

def cast_from_ptr(TYPE, x):
    return lltype.cast_opaque_ptr(TYPE, x)


def new_frame(memocast, is_oo):
    if is_oo:
        frame = OOFrame(memocast)
    else:
        frame = Frame(memocast)
    return _to_opaque(frame)

_future_values = []

def frame_clear(frame, loop):
    frame = _from_opaque(frame)
    loop = _from_opaque(loop)
    frame.loop = loop
    frame.env = {}
    for i in range(len(loop.inputargs)):
        frame.env[loop.inputargs[i]] = _future_values[i]
    del _future_values[:]

def set_future_value_int(index, value):
    del _future_values[index:]
    assert len(_future_values) == index
    _future_values.append(value)

def set_future_value_ptr(index, value):
    del _future_values[index:]
    assert len(_future_values) == index
    _future_values.append(value)

def set_future_value_obj(index, value):
    del _future_values[index:]
    assert len(_future_values) == index
    _future_values.append(value)

def frame_execute(frame):
    frame = _from_opaque(frame)
    if frame.verbose:
        values = [frame.env[v] for v in frame.loop.inputargs]
        log.trace('Entering CPU frame <- %r' % (values,))
    try:
        result = frame.execute()
        if frame.verbose:
            log.trace('Leaving CPU frame -> #%d' % (result,))
            frame.log_progress()
    except Exception, e:
        log.ERROR('%s in CPU frame: %s' % (e.__class__.__name__, e))
        # Only invoke pdb when io capturing is not on otherwise py.io complains.
        if py.test.config.option.nocapture:
            import sys, pdb
            pdb.post_mortem(sys.exc_info()[2])
        raise
    del frame.env
    return result

def frame_int_getvalue(frame, num):
    frame = _from_opaque(frame)
    return frame.fail_args[num]

def frame_ptr_getvalue(frame, num):
    frame = _from_opaque(frame)
    result = frame.fail_args[num]
    frame.fail_args[num] = None
    return result

_last_exception = None

def get_exception():
    if _last_exception:
        return llmemory.cast_ptr_to_adr(_last_exception.args[0])
    else:
        return llmemory.NULL

def get_exc_value():
    if _last_exception:
        return lltype.cast_opaque_ptr(llmemory.GCREF, _last_exception.args[1])
    else:
        return lltype.nullptr(llmemory.GCREF.TO)

def clear_exception():
    global _last_exception
    _last_exception = None

_pseudo_exceptions = {}

def _set_error(Class):
    global _last_exception
    if _llinterp.typer is not None:
        llframe = _llinterp.frame_class(None, None, _llinterp)
        try:
            llframe.make_llexception(Class())
        except LLException, e:
            _last_exception = e
        else:
            assert 0, "should have raised"
    else:
        # for tests, a random emulated ll_inst will do
        if Class not in _pseudo_exceptions:
            ll_inst = lltype.malloc(rclass.OBJECT)
            ll_inst.typeptr = lltype.malloc(rclass.OBJECT_VTABLE,
                                            immortal=True)
            _pseudo_exceptions[Class] = LLException(ll_inst.typeptr, ll_inst)
        _last_exception = _pseudo_exceptions[Class]

def set_overflow_error():
    _set_error(OverflowError)

def set_zero_division_error():
    _set_error(ZeroDivisionError)

class MemoCast(object):
    def __init__(self):
        self.addresses = [llmemory.NULL]
        self.rev_cache = {}

def new_memo_cast():
    memocast = MemoCast()
    return _to_opaque(memocast)

def cast_adr_to_int(memocast, adr):
    # xxx slow
    assert lltype.typeOf(adr) == llmemory.Address
    memocast = _from_opaque(memocast)
    addresses = memocast.addresses
    for i in xrange(len(addresses)-1, -1, -1):
        if addresses[i] == adr:
            return i
    i = len(addresses)
    addresses.append(adr)
    return i

def cast_int_to_adr(memocast, int):
    memocast = _from_opaque(memocast)
    assert 0 <= int < len(memocast.addresses)
    return memocast.addresses[int]

class GuardFailed(Exception):
    pass

# ____________________________________________________________


def do_arraylen_gc(arraydescr, array):
    array = array._obj.container
    return array.getlength()

def do_strlen(_, string):
    str = lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR), string)
    return len(str.chars)

def do_strgetitem(_, string, index):
    str = lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR), string)
    return ord(str.chars[index])

def do_unicodelen(_, string):
    uni = lltype.cast_opaque_ptr(lltype.Ptr(rstr.UNICODE), string)
    return len(uni.chars)

def do_unicodegetitem(_, string, index):
    uni = lltype.cast_opaque_ptr(lltype.Ptr(rstr.UNICODE), string)
    return ord(uni.chars[index])

def do_getarrayitem_gc_int(array, index, memocast):
    array = array._obj.container
    return cast_to_int(array.getitem(index), memocast)

def do_getarrayitem_gc_ptr(array, index):
    array = array._obj.container
    return cast_to_ptr(array.getitem(index))

def do_getfield_gc_int(struct, fieldnum, memocast):
    STRUCT, fieldname = symbolic.TokenToField[fieldnum]
    ptr = lltype.cast_opaque_ptr(lltype.Ptr(STRUCT), struct)
    x = getattr(ptr, fieldname)
    return cast_to_int(x, memocast)

def do_getfield_gc_ptr(struct, fieldnum):
    STRUCT, fieldname = symbolic.TokenToField[fieldnum]
    ptr = lltype.cast_opaque_ptr(lltype.Ptr(STRUCT), struct)
    x = getattr(ptr, fieldname)
    return cast_to_ptr(x)

def do_getfield_raw_int(struct, fieldnum, memocast):
    STRUCT, fieldname = symbolic.TokenToField[fieldnum]
    ptr = llmemory.cast_adr_to_ptr(struct, lltype.Ptr(STRUCT))
    x = getattr(ptr, fieldname)
    return cast_to_int(x, memocast)

def do_getfield_raw_ptr(struct, fieldnum):
    STRUCT, fieldname = symbolic.TokenToField[fieldnum]
    ptr = llmemory.cast_adr_to_ptr(struct, lltype.Ptr(STRUCT))
    x = getattr(ptr, fieldname)
    return cast_to_ptr(x)

def do_new(size):
    TYPE = symbolic.Size2Type[size]
    x = lltype.malloc(TYPE)
    return cast_to_ptr(x)

def do_new_array(arraynum, count):
    TYPE = symbolic.Size2Type[arraynum]
    x = lltype.malloc(TYPE, count)
    return cast_to_ptr(x)

def do_setarrayitem_gc_int(array, index, newvalue, memocast):
    array = array._obj.container
    ITEMTYPE = lltype.typeOf(array).OF
    newvalue = cast_from_int(ITEMTYPE, newvalue, memocast)
    array.setitem(index, newvalue)

def do_setarrayitem_gc_ptr(array, index, newvalue):
    array = array._obj.container
    ITEMTYPE = lltype.typeOf(array).OF
    newvalue = cast_from_ptr(ITEMTYPE, newvalue)
    array.setitem(index, newvalue)

def do_setfield_gc_int(struct, fieldnum, newvalue, memocast):
    STRUCT, fieldname = symbolic.TokenToField[fieldnum]
    ptr = lltype.cast_opaque_ptr(lltype.Ptr(STRUCT), struct)
    FIELDTYPE = getattr(STRUCT, fieldname)
    newvalue = cast_from_int(FIELDTYPE, newvalue, memocast)
    setattr(ptr, fieldname, newvalue)

def do_setfield_gc_ptr(struct, fieldnum, newvalue):
    STRUCT, fieldname = symbolic.TokenToField[fieldnum]
    ptr = lltype.cast_opaque_ptr(lltype.Ptr(STRUCT), struct)
    FIELDTYPE = getattr(STRUCT, fieldname)
    newvalue = cast_from_ptr(FIELDTYPE, newvalue)
    setattr(ptr, fieldname, newvalue)

def do_setfield_raw_int(struct, fieldnum, newvalue, memocast):
    STRUCT, fieldname = symbolic.TokenToField[fieldnum]
    ptr = llmemory.cast_adr_to_ptr(struct, lltype.Ptr(STRUCT))
    FIELDTYPE = getattr(STRUCT, fieldname)
    newvalue = cast_from_int(FIELDTYPE, newvalue, memocast)
    setattr(ptr, fieldname, newvalue)

def do_setfield_raw_ptr(struct, fieldnum, newvalue):
    STRUCT, fieldname = symbolic.TokenToField[fieldnum]
    ptr = llmemory.cast_adr_to_ptr(struct, lltype.Ptr(STRUCT))
    FIELDTYPE = getattr(STRUCT, fieldname)
    newvalue = cast_from_ptr(FIELDTYPE, newvalue)
    setattr(ptr, fieldname, newvalue)

def do_newstr(_, length):
    x = rstr.mallocstr(length)
    return cast_to_ptr(x)

def do_newunicode(_, length):
    return cast_to_ptr(rstr.mallocunicode(length))

def do_strsetitem(_, string, index, newvalue):
    str = lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR), string)
    str.chars[index] = chr(newvalue)

def do_unicodesetitem(_, string, index, newvalue):
    uni = lltype.cast_opaque_ptr(lltype.Ptr(rstr.UNICODE), string)
    uni.chars[index] = unichr(newvalue)

# ---------- call ----------

_call_args = []

def do_call_pushint(x):
    _call_args.append(x)

def do_call_pushptr(x):
    _call_args.append(x)

def _do_call_common(f, memocast, err_result=None):
    global _last_exception
    assert _last_exception is None, "exception left behind"
    ptr = cast_int_to_adr(memocast, f).ptr
    FUNC = lltype.typeOf(ptr).TO
    ARGS = FUNC.ARGS
    args = cast_call_args(ARGS, _call_args, memocast)
    del _call_args[:]
    assert len(ARGS) == len(args)
    try:
        if hasattr(ptr._obj, 'graph'):
            llinterp = _llinterp      # it's a global set here by CPU.__init__()
            result = llinterp.eval_graph(ptr._obj.graph, args)
        else:
            result = ptr._obj._callable(*args)
    except LLException, e:
        _last_exception = e
        result = err_result
    return result

def do_call_void(f, memocast):
    _do_call_common(f, memocast)

def do_call_int(f, memocast):
    x = _do_call_common(f, memocast, 0)
    return cast_to_int(x, memocast)

def do_call_ptr(f, memocast):
    x = _do_call_common(f, memocast, lltype.nullptr(llmemory.GCREF.TO))
    return cast_to_ptr(x)

def cast_call_args(ARGS, args, memocast):
    argsiter = iter(args)
    args = []
    for TYPE in ARGS:
        if TYPE is lltype.Void:
            x = None
        else:
            x = argsiter.next()
            if isinstance(TYPE, ootype.OOType):
                x = ootype.cast_from_object(TYPE, x)
            elif isinstance(TYPE, lltype.Ptr) and TYPE.TO._gckind == 'gc':
                x = cast_from_ptr(TYPE, x)
            else:
                x = cast_from_int(TYPE, x, memocast)
        args.append(x)
    assert list(argsiter) == []
    return args


# for ootype meth and staticmeth
def call_maybe_on_top_of_llinterp(meth, args):
    global _last_exception
    if isinstance(meth, ootype._bound_meth):
        mymethod = meth.meth
        myargs = [meth.inst] + list(args)
    else:
        mymethod = meth
        myargs = args
    if hasattr(mymethod, 'graph'):
        llinterp = _llinterp      # it's a global set here by CPU.__init__()
        try:
            result = llinterp.eval_graph(mymethod.graph, myargs)
        except LLException, e:
            _last_exception = e
            result = get_err_result_for_type(mymethod._TYPE.RESULT)
    else:
        result = meth(*args)  # no exception support in this case
    return result

def get_err_result_for_type(T):
    if T is ootype.Void:
        return None
    elif isinstance(T, ootype.OOType):
        return ootype.null(T)
    else:
        return 0

# ____________________________________________________________


def setannotation(func, annotation, specialize_as_constant=False):

    class Entry(ExtRegistryEntry):
        "Annotation and specialization for calls to 'func'."
        _about_ = func

        if annotation is None or isinstance(annotation, annmodel.SomeObject):
            s_result_annotation = annotation
        else:
            def compute_result_annotation(self, *args_s):
                return annotation(*args_s)

        if specialize_as_constant:
            def specialize_call(self, hop):
                llvalue = func(hop.args_s[0].const)
                return hop.inputconst(lltype.typeOf(llvalue), llvalue)
        else:
            # specialize as direct_call
            def specialize_call(self, hop):
                ARGS = [r.lowleveltype for r in hop.args_r]
                RESULT = hop.r_result.lowleveltype
                if hop.rtyper.type_system.name == 'lltypesystem':
                    FUNCTYPE = lltype.FuncType(ARGS, RESULT)
                    funcptr = lltype.functionptr(FUNCTYPE, func.__name__,
                                                 _callable=func, _debugexc=True)
                    cfunc = hop.inputconst(lltype.Ptr(FUNCTYPE), funcptr)
                else:
                    FUNCTYPE = ootype.StaticMethod(ARGS, RESULT)
                    sm = ootype._static_meth(FUNCTYPE, _name=func.__name__, _callable=func)
                    cfunc = hop.inputconst(FUNCTYPE, sm)
                args_v = hop.inputargs(*hop.args_r)
                return hop.genop('direct_call', [cfunc] + args_v, hop.r_result)


COMPILEDLOOP = lltype.Ptr(lltype.OpaqueType("CompiledLoop"))
FRAME = lltype.Ptr(lltype.OpaqueType("Frame"))
OOFRAME = lltype.Ptr(lltype.OpaqueType("OOFrame"))
MEMOCAST = lltype.Ptr(lltype.OpaqueType("MemoCast"))

_TO_OPAQUE[CompiledLoop] = COMPILEDLOOP.TO
_TO_OPAQUE[Frame] = FRAME.TO
_TO_OPAQUE[OOFrame] = OOFRAME.TO
_TO_OPAQUE[MemoCast] = MEMOCAST.TO

s_CompiledLoop = annmodel.SomePtr(COMPILEDLOOP)
s_Frame = annmodel.SomePtr(FRAME)
s_MemoCast = annmodel.SomePtr(MEMOCAST)

setannotation(compile_start, s_CompiledLoop)
setannotation(compile_start_int_var, annmodel.SomeInteger())
setannotation(compile_start_ptr_var, annmodel.SomeInteger())
setannotation(compile_start_obj_var, annmodel.SomeInteger())
setannotation(compile_add, annmodel.s_None)
setannotation(compile_add_descr, annmodel.s_None)
setannotation(compile_add_var, annmodel.s_None)
setannotation(compile_add_int_const, annmodel.s_None)
setannotation(compile_add_ptr_const, annmodel.s_None)
setannotation(compile_add_int_result, annmodel.SomeInteger())
setannotation(compile_add_ptr_result, annmodel.SomeInteger())
setannotation(compile_add_jump_target, annmodel.s_None)
setannotation(compile_add_fail, annmodel.s_None)
setannotation(compile_suboperations, s_CompiledLoop)
setannotation(compile_redirect_code, annmodel.s_None)

setannotation(new_frame, s_Frame)
setannotation(frame_clear, annmodel.s_None)
setannotation(set_future_value_int, annmodel.s_None)
setannotation(set_future_value_ptr, annmodel.s_None)
setannotation(set_future_value_obj, annmodel.s_None)
setannotation(frame_execute, annmodel.SomeInteger())
setannotation(frame_int_getvalue, annmodel.SomeInteger())
setannotation(frame_ptr_getvalue, annmodel.SomePtr(llmemory.GCREF))

setannotation(get_exception, annmodel.SomeAddress())
setannotation(get_exc_value, annmodel.SomePtr(llmemory.GCREF))
setannotation(clear_exception, annmodel.s_None)
setannotation(set_overflow_error, annmodel.s_None)
setannotation(set_zero_division_error, annmodel.s_None)

setannotation(new_memo_cast, s_MemoCast)
setannotation(cast_adr_to_int, annmodel.SomeInteger())
setannotation(cast_int_to_adr, annmodel.SomeAddress())

setannotation(do_arraylen_gc, annmodel.SomeInteger())
setannotation(do_strlen, annmodel.SomeInteger())
setannotation(do_strgetitem, annmodel.SomeInteger())
setannotation(do_unicodelen, annmodel.SomeInteger())
setannotation(do_unicodegetitem, annmodel.SomeInteger())
setannotation(do_getarrayitem_gc_int, annmodel.SomeInteger())
setannotation(do_getarrayitem_gc_ptr, annmodel.SomePtr(llmemory.GCREF))
setannotation(do_getfield_gc_int, annmodel.SomeInteger())
setannotation(do_getfield_gc_ptr, annmodel.SomePtr(llmemory.GCREF))
setannotation(do_getfield_raw_int, annmodel.SomeInteger())
setannotation(do_getfield_raw_ptr, annmodel.SomePtr(llmemory.GCREF))
setannotation(do_new, annmodel.SomePtr(llmemory.GCREF))
setannotation(do_new_array, annmodel.SomePtr(llmemory.GCREF))
setannotation(do_setarrayitem_gc_int, annmodel.s_None)
setannotation(do_setarrayitem_gc_ptr, annmodel.s_None)
setannotation(do_setfield_gc_int, annmodel.s_None)
setannotation(do_setfield_gc_ptr, annmodel.s_None)
setannotation(do_setfield_raw_int, annmodel.s_None)
setannotation(do_setfield_raw_ptr, annmodel.s_None)
setannotation(do_newstr, annmodel.SomePtr(llmemory.GCREF))
setannotation(do_strsetitem, annmodel.s_None)
setannotation(do_newunicode, annmodel.SomePtr(llmemory.GCREF))
setannotation(do_unicodesetitem, annmodel.s_None)
setannotation(do_call_pushint, annmodel.s_None)
setannotation(do_call_pushptr, annmodel.s_None)
setannotation(do_call_int, annmodel.SomeInteger())
setannotation(do_call_ptr, annmodel.SomePtr(llmemory.GCREF))
setannotation(do_call_void, annmodel.s_None)
