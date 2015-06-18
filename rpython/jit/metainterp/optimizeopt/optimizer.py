from rpython.jit.metainterp import jitprof, resume, compile
from rpython.jit.metainterp.executor import execute_nonspec
from rpython.jit.metainterp.history import BoxInt, BoxFloat, Const, ConstInt,\
     REF, BoxPtr, ConstPtr, ConstFloat
from rpython.jit.metainterp.optimizeopt.intutils import IntBound, IntUnbounded,\
                                                     IntLowerBound, MININT,\
                                                     MAXINT
from rpython.jit.metainterp.optimizeopt.util import make_dispatcher_method
from rpython.jit.metainterp.resoperation import rop, ResOperation,\
     AbstractResOp, GuardResOp
from rpython.jit.metainterp.typesystem import llhelper
from rpython.tool.pairtype import extendabletype
from rpython.rlib.debug import debug_print
from rpython.rlib.objectmodel import specialize

""" The tag field on OptValue has a following meaning:

lower two bits are LEVEL
next 16 bits is the position in the original list, 0 if unknown or a constant
"""

LEVEL_UNKNOWN    = 0
LEVEL_NONNULL    = 1
LEVEL_KNOWNCLASS = 2     # might also mean KNOWNARRAYDESCR, for arrays
LEVEL_CONSTANT   = 3

MODE_ARRAY   = '\x00'
MODE_STR     = '\x01'
MODE_UNICODE = '\x02'


class LenBound(object):
    def __init__(self, mode, descr, bound):
        self.mode = mode
        self.descr = descr
        self.bound = bound

    def clone(self):
        return LenBound(self.mode, self.descr, self.bound.clone())

    def generalization_of(self, other):
        return (other is not None and
                self.mode == other.mode and
                self.descr == other.descr and
                self.bound.contains_bound(other.bound))

class OptValue(object):
    __metaclass__ = extendabletype
    _attrs_ = ('box', '_tag')

    _tag = 0

    def __init__(self, box, level=None, known_class=None, intbound=None):
        self.box = box
        if level is not None:
            self._tag = level

        if isinstance(box, Const):
            self.make_constant(box)
        # invariant: box is a Const if and only if level == LEVEL_CONSTANT

    def __repr__(self):
        level = {LEVEL_UNKNOWN: 'UNKNOWN',
                 LEVEL_NONNULL: 'NONNULL',
                 LEVEL_KNOWNCLASS: 'KNOWNCLASS',
                 LEVEL_CONSTANT: 'CONSTANT'}.get(self.getlevel(),
                                                 self.getlevel())
        return '<%s %s %s>' % (
            self.__class__.__name__,
            level,
            self.box)

    def getlevel(self):
        return self._tag & 0x3

    def setlevel(self, level):
        self._tag = (self._tag & (~0x3)) | level

    def import_from(self, other, optimizer):
        if self.getlevel() == LEVEL_CONSTANT:
            assert other.getlevel() == LEVEL_CONSTANT
            assert other.box.same_constant(self.box)
            return
        assert self.getlevel() <= LEVEL_NONNULL
        if other.getlevel() == LEVEL_CONSTANT:
            self.make_constant(other.get_key_box())
        elif other.getlevel() == LEVEL_KNOWNCLASS:
            self.make_constant_class(None, other.get_known_class())
        else:
            if other.getlevel() == LEVEL_NONNULL:
                self.ensure_nonnull()

    def make_guards(self, box):
        if self.getlevel() == LEVEL_CONSTANT:
            op = ResOperation(rop.GUARD_VALUE, [box, self.box], None)
            return [op]
        return []

    def copy_from(self, other_value):
        assert isinstance(other_value, OptValue)
        self.box = other_value.box
        self._tag = other_value._tag

    def force_box(self, optforce):
        return self.box

    def get_key_box(self):
        return self.box

    def force_at_end_of_preamble(self, already_forced, optforce):
        return self

    # visitor API

    def visitor_walk_recursive(self, visitor):
        pass

    @specialize.argtype(1)
    def visitor_dispatch_virtual_type(self, visitor):
        if self.is_virtual():
            return self._visitor_dispatch_virtual_type(visitor)
        else:
            return visitor.visit_not_virtual(self)

    @specialize.argtype(1)
    def _visitor_dispatch_virtual_type(self, visitor):
        assert 0, "unreachable"

    def is_constant(self):
        return self.getlevel() == LEVEL_CONSTANT

    def is_null(self):
        if self.is_constant():
            box = self.box
            assert isinstance(box, Const)
            return not box.nonnull()
        return False

    def same_value(self, other):
        if not other:
            return False
        if self.is_constant() and other.is_constant():
            return self.box.same_constant(other.box)
        return self is other

    def is_nonnull(self):
        level = self.getlevel()
        if level == LEVEL_NONNULL or level == LEVEL_KNOWNCLASS:
            return True
        elif level == LEVEL_CONSTANT:
            box = self.box
            assert isinstance(box, Const)
            return box.nonnull()
        else:
            return False

    def ensure_nonnull(self):
        if self.getlevel() < LEVEL_NONNULL:
            self.setlevel(LEVEL_NONNULL)

    def get_constant_int(self):
        assert self.is_constant()
        box = self.box
        assert isinstance(box, ConstInt)
        return box.getint()

    def is_virtual(self):
        # Don't check this with 'isinstance(_, VirtualValue)'!
        # Even if it is a VirtualValue, the 'box' can be non-None,
        # meaning it has been forced.
        return self.box is None

    def is_forced_virtual(self):
        return False

    def getfield(self, ofs, default):
        raise NotImplementedError

    def setfield(self, ofs, value):
        raise NotImplementedError

    def getlength(self):
        raise NotImplementedError

    def getitem(self, index):
        raise NotImplementedError

    def setitem(self, index, value):
        raise NotImplementedError

    def getitem_raw(self, offset, length, descr):
        raise NotImplementedError

    def setitem_raw(self, offset, length, descr, value):
        raise NotImplementedError

    def getinteriorfield(self, index, ofs, default):
        raise NotImplementedError

    def setinteriorfield(self, index, ofs, value):
        raise NotImplementedError

    def get_missing_null_value(self):
        raise NotImplementedError    # only for VArrayValue

    def make_constant(self, constbox):
        """Replace 'self.box' with a Const box."""
        assert isinstance(constbox, Const)
        self.box = constbox
        self.setlevel(LEVEL_CONSTANT)

    def get_last_guard(self, optimizer):
        return None

    def get_known_class(self):
        return None

    def getlenbound(self):
        return None

    def getintbound(self):
        return None

    def get_constant_class(self, cpu):
        return None

class PtrOptValue(OptValue):
    _attrs_ = ('known_class', 'last_guard_pos', 'lenbound')

    known_class = None
    last_guard_pos = -1
    lenbound = None

    def __init__(self, box, level=None, known_class=None, intbound=None):
        OptValue.__init__(self, box, level, None, intbound)
        if not isinstance(box, Const):
            self.known_class = known_class

    def copy_from(self, other_value):
        assert isinstance(other_value, PtrOptValue)
        self.box = other_value.box
        self.known_class = other_value.known_class
        self._tag = other_value._tag
        self.last_guard_pos = other_value.last_guard_pos
        self.lenbound = other_value.lenbound

    def make_len_gt(self, mode, descr, val):
        if self.lenbound:
            if self.lenbound.mode != mode or self.lenbound.descr != descr:
                # XXX a rare case?  it seems to occur sometimes when
                # running lib-python's test_io.py in PyPy on Linux 32...
                from rpython.jit.metainterp.optimize import InvalidLoop
                raise InvalidLoop("bad mode/descr")
            self.lenbound.bound.make_gt(IntBound(val, val))
        else:
            self.lenbound = LenBound(mode, descr, IntLowerBound(val + 1))

    def make_nonnull(self, optimizer):
        assert self.getlevel() < LEVEL_NONNULL
        self.setlevel(LEVEL_NONNULL)
        if optimizer is not None:
            self.last_guard_pos = len(optimizer._newoperations) - 1
            assert self.get_last_guard(optimizer).is_guard()

    def make_constant_class(self, optimizer, classbox):
        assert self.getlevel() < LEVEL_KNOWNCLASS
        self.known_class = classbox
        self.setlevel(LEVEL_KNOWNCLASS)
        if optimizer is not None:
            self.last_guard_pos = len(optimizer._newoperations) - 1
            assert self.get_last_guard(optimizer).is_guard()

    def import_from(self, other, optimizer):
        OptValue.import_from(self, other, optimizer)
        if self.getlevel() != LEVEL_CONSTANT:
            if other.getlenbound():
                if self.lenbound:
                    assert other.getlenbound().mode == self.lenbound.mode
                    assert other.getlenbound().descr == self.lenbound.descr
                    self.lenbound.bound.intersect(other.getlenbound().bound)
                else:
                    self.lenbound = other.getlenbound().clone()

    def make_guards(self, box):
        guards = []
        level = self.getlevel()
        if level == LEVEL_CONSTANT:
            op = ResOperation(rop.GUARD_VALUE, [box, self.box], None)
            guards.append(op)
        elif level == LEVEL_KNOWNCLASS:
            op = ResOperation(rop.GUARD_NONNULL_CLASS,
                              [box, self.known_class], None)
            guards.append(op)
        else:
            if level == LEVEL_NONNULL:
                op = ResOperation(rop.GUARD_NONNULL, [box], None)
                guards.append(op)
            if self.lenbound:
                lenbox = BoxInt()
                if self.lenbound.mode == MODE_ARRAY:
                    op = ResOperation(rop.ARRAYLEN_GC, [box], lenbox, self.lenbound.descr)
                elif self.lenbound.mode == MODE_STR:
                    op = ResOperation(rop.STRLEN, [box], lenbox, self.lenbound.descr)
                elif self.lenbound.mode == MODE_UNICODE:
                    op = ResOperation(rop.UNICODELEN, [box], lenbox, self.lenbound.descr)
                else:
                    debug_print("Unknown lenbound mode")
                    assert False
                guards.append(op)
                self.lenbound.bound.make_guards(lenbox, guards)
        return guards

    def get_constant_class(self, cpu):
        level = self.getlevel()
        if level == LEVEL_KNOWNCLASS:
            return self.known_class
        elif level == LEVEL_CONSTANT and not self.is_null():
            return cpu.ts.cls_of_box(self.box)
        else:
            return None

    def getlenbound(self):
        return self.lenbound

    def get_last_guard(self, optimizer):
        if self.last_guard_pos == -1:
            return None
        return optimizer._newoperations[self.last_guard_pos]

    def get_known_class(self):
        return self.known_class

class IntOptValue(OptValue):
    _attrs_ = ('intbound',)

    def __init__(self, box, level=None, known_class=None, intbound=None):
        OptValue.__init__(self, box, level, None, None)
        if isinstance(box, Const):
            value = box.getint()
            self.intbound = IntBound(value, value)
            return
        if intbound:
            self.intbound = intbound
        else:
            assert isinstance(box, BoxInt)
            self.intbound = IntBound(MININT, MAXINT)

    def copy_from(self, other_value):
        assert isinstance(other_value, IntOptValue)
        self.box = other_value.box
        self.intbound = other_value.intbound
        self._tag = other_value._tag

    def make_constant(self, constbox):
        """Replace 'self.box' with a Const box."""
        assert isinstance(constbox, ConstInt)
        self.box = constbox
        self.setlevel(LEVEL_CONSTANT)
        val = constbox.getint()
        self.intbound = IntBound(val, val)

    def is_nonnull(self):
        if OptValue.is_nonnull(self):
            return True
        if self.intbound:
            if self.intbound.known_gt(IntBound(0, 0)) or \
               self.intbound.known_lt(IntBound(0, 0)):
                return True
        return False

    def make_nonnull(self, optimizer):
        assert self.getlevel() < LEVEL_NONNULL
        self.setlevel(LEVEL_NONNULL)

    def import_from(self, other, optimizer):
        OptValue.import_from(self, other, optimizer)
        if self.getlevel() != LEVEL_CONSTANT:
            if other.getintbound() is not None: # VRawBufferValue
                self.intbound.intersect(other.getintbound())

    def make_guards(self, box):
        guards = []
        level = self.getlevel()
        if level == LEVEL_CONSTANT:
            op = ResOperation(rop.GUARD_VALUE, [box, self.box], None)
            guards.append(op)
        elif level == LEVEL_KNOWNCLASS:
            op = ResOperation(rop.GUARD_NONNULL, [box], None)
            guards.append(op)
        else:
            if level == LEVEL_NONNULL:
                op = ResOperation(rop.GUARD_NONNULL, [box], None)
                guards.append(op)
            self.intbound.make_guards(box, guards)
        return guards

    def getintbound(self):
        return self.intbound

    def get_last_guard(self, optimizer):
        return None

    def get_known_class(self):
        return None

    def getlenbound(self):
        return None

class ConstantFloatValue(OptValue):
    def __init__(self, box):
        self.make_constant(box)

    def __repr__(self):
        return 'Constant(%r)' % (self.box,)

class ConstantIntValue(IntOptValue):
    def __init__(self, box):
        self.make_constant(box)

    def __repr__(self):
        return 'Constant(%r)' % (self.box,)

class ConstantPtrValue(PtrOptValue):
    def __init__(self, box):
        self.make_constant(box)

    def __repr__(self):
        return 'Constant(%r)' % (self.box,)

CONST_0      = ConstInt(0)
CONST_1      = ConstInt(1)
CVAL_ZERO    = ConstantIntValue(CONST_0)
CVAL_ZERO_FLOAT = ConstantFloatValue(Const._new(0.0))
llhelper.CVAL_NULLREF = ConstantPtrValue(llhelper.CONST_NULL)
REMOVED = AbstractResOp(None)


class Optimization(object):
    next_optimization = None

    def __init__(self):
        pass # make rpython happy

    def propagate_forward(self, op):
        raise NotImplementedError

    def emit_operation(self, op):
        self.last_emitted_operation = op
        self.next_optimization.propagate_forward(op)

    # FIXME: Move some of these here?
    def getvalue(self, box):
        return self.optimizer.getvalue(box)

    def make_constant(self, box, constbox):
        return self.optimizer.make_constant(box, constbox)

    def make_constant_int(self, box, intconst):
        return self.optimizer.make_constant_int(box, intconst)

    def make_equal_to(self, box, value, replace=False):
        return self.optimizer.make_equal_to(box, value, replace=replace)

    def get_constant_box(self, box):
        return self.optimizer.get_constant_box(box)

    def new_box(self, fieldofs):
        return self.optimizer.new_box(fieldofs)

    def new_const(self, fieldofs):
        return self.optimizer.new_const(fieldofs)

    def new_box_item(self, arraydescr):
        return self.optimizer.new_box_item(arraydescr)

    def new_const_item(self, arraydescr):
        return self.optimizer.new_const_item(arraydescr)

    def pure(self, opnum, args, result):
        if self.optimizer.optpure:
            self.optimizer.optpure.pure(opnum, args, result)

    def has_pure_result(self, opnum, args, descr):
        if self.optimizer.optpure:
            return self.optimizer.optpure.has_pure_result(opnum, args, descr)
        return False

    def get_pure_result(self, key):
        if self.optimizer.optpure:
            return self.optimizer.optpure.get_pure_result(key)
        return None

    def setup(self):
        pass

    def force_at_end_of_preamble(self):
        pass

    # Called after last operation has been propagated to flush out any posponed ops
    def flush(self):
        pass

    def produce_potential_short_preamble_ops(self, potential_ops):
        pass

    def forget_numberings(self, box):
        self.optimizer.forget_numberings(box)

    def _can_optimize_call_pure(self, op):
        arg_consts = []
        for i in range(op.numargs()):
            arg = op.getarg(i)
            const = self.optimizer.get_constant_box(arg)
            if const is None:
                return None
            arg_consts.append(const)
        else:
            # all constant arguments: check if we already know the result
            try:
                return self.optimizer.call_pure_results[arg_consts]
            except KeyError:
                return None


class Optimizer(Optimization):

    exporting_state = False

    def __init__(self, metainterp_sd, jitdriver_sd, loop, optimizations=None):
        self.metainterp_sd = metainterp_sd
        self.jitdriver_sd = jitdriver_sd
        self.cpu = metainterp_sd.cpu
        self.loop = loop
        self.values = {}
        self.interned_refs = self.cpu.ts.new_ref_dict()
        self.interned_ints = {}
        self.resumedata_memo = resume.ResumeDataLoopMemo(metainterp_sd)
        self.bool_boxes = {}
        self.producer = {}
        self.pendingfields = None # set temporarily to a list, normally by
                                  # heap.py, as we're about to generate a guard
        self.quasi_immutable_deps = None
        self.opaque_pointers = {}
        self.replaces_guard = {}
        self._newoperations = []
        self.optimizer = self
        self.optpure = None
        self.optheap = None
        self.optearlyforce = None
        # the following two fields is the data kept for unrolling,
        # those are the operations that can go to the short_preamble
        if loop is not None:
            self.call_pure_results = loop.call_pure_results

        self.set_optimizations(optimizations)
        self.setup()

    def set_optimizations(self, optimizations):
        if optimizations:
            self.first_optimization = optimizations[0]
            for i in range(1, len(optimizations)):
                optimizations[i - 1].next_optimization = optimizations[i]
            optimizations[-1].next_optimization = self
            for o in optimizations:
                o.optimizer = self
                o.last_emitted_operation = None
                o.setup()
        else:
            optimizations = []
            self.first_optimization = self

        self.optimizations  = optimizations

    def replace_guard(self, op, value):
        assert isinstance(value, PtrOptValue)
        if value.last_guard_pos == -1:
            return
        self.replaces_guard[op] = value.last_guard_pos

    def force_at_end_of_preamble(self):
        for o in self.optimizations:
            o.force_at_end_of_preamble()

    def flush(self):
        for o in self.optimizations:
            o.flush()

    def produce_potential_short_preamble_ops(self, sb):
        for opt in self.optimizations:
            opt.produce_potential_short_preamble_ops(sb)

    def forget_numberings(self, virtualbox):
        self.metainterp_sd.profiler.count(jitprof.Counters.OPT_FORCINGS)
        self.resumedata_memo.forget_numberings(virtualbox)

    def getinterned(self, box):
        constbox = self.get_constant_box(box)
        if constbox is None:
            return box
        if constbox.type == REF:
            value = constbox.getref_base()
            if not value:
                return box
            return self.interned_refs.setdefault(value, box)
        #elif constbox.type == INT:
        #    value = constbox.getint()
        #    return self.interned_ints.setdefault(value, box)
        else:
            return box

    @specialize.argtype(0)
    def getvalue(self, box):
        box = self.getinterned(box)
        try:
            value = self.values[box]
        except KeyError:
            if isinstance(box, BoxPtr) or isinstance(box, ConstPtr):
                value = self.values[box] = PtrOptValue(box)
            elif isinstance(box, BoxInt) or isinstance(box, ConstInt):
                value = self.values[box] = IntOptValue(box)
            else:
                value = self.values[box] = OptValue(box)
        self.ensure_imported(value)
        return value

    def get_box_replacement(self, box):
        try:
            v = self.values[box]
        except KeyError:
            return box
        return v.get_key_box()

    def ensure_imported(self, value):
        pass

    @specialize.argtype(0)
    def get_constant_box(self, box):
        if isinstance(box, Const):
            return box
        try:
            value = self.values[box]
            self.ensure_imported(value)
        except KeyError:
            return None
        if value.is_constant():
            constbox = value.box
            assert isinstance(constbox, Const)
            return constbox
        return None

    def get_newoperations(self):
        self.flush()
        return self._newoperations

    def clear_newoperations(self):
        self._newoperations = []

    def make_equal_to(self, box, value, replace=False):
        assert isinstance(value, OptValue)
        if replace:
            try:
                cur_value = self.values[box]
            except KeyError:
                pass
            else:
                assert cur_value.getlevel() != LEVEL_CONSTANT
                # replacing with a different box
                cur_value.copy_from(value)
                return
        self.values[box] = value

    def make_constant(self, box, constbox):
        if isinstance(constbox, ConstInt):
            self.make_equal_to(box, ConstantIntValue(constbox))
        elif isinstance(constbox, ConstPtr):
            self.make_equal_to(box, ConstantPtrValue(constbox))
        elif isinstance(constbox, ConstFloat):
            self.make_equal_to(box, ConstantFloatValue(constbox))
        else:
            assert False

    def make_constant_int(self, box, intvalue):
        self.make_constant(box, ConstInt(intvalue))

    def new_ptr_box(self):
        return self.cpu.ts.BoxRef()

    def new_box(self, fieldofs):
        if fieldofs.is_pointer_field():
            return self.new_ptr_box()
        elif fieldofs.is_float_field():
            return BoxFloat()
        else:
            return BoxInt()

    def new_const(self, fieldofs):
        if fieldofs.is_pointer_field():
            return self.cpu.ts.CVAL_NULLREF
        elif fieldofs.is_float_field():
            return CVAL_ZERO_FLOAT
        else:
            return CVAL_ZERO

    def new_box_item(self, arraydescr):
        if arraydescr.is_array_of_pointers():
            return self.new_ptr_box()
        elif arraydescr.is_array_of_floats():
            return BoxFloat()
        else:
            return BoxInt()

    def new_const_item(self, arraydescr):
        if arraydescr.is_array_of_pointers():
            return self.cpu.ts.CVAL_NULLREF
        elif arraydescr.is_array_of_floats():
            return CVAL_ZERO_FLOAT
        else:
            return CVAL_ZERO

    def propagate_all_forward(self, clear=True):
        if clear:
            self.clear_newoperations()
        for op in self.loop.operations:
            self.first_optimization.propagate_forward(op)
        self.loop.operations = self.get_newoperations()
        self.loop.quasi_immutable_deps = self.quasi_immutable_deps
        # accumulate counters
        self.resumedata_memo.update_counters(self.metainterp_sd.profiler)

    def send_extra_operation(self, op):
        self.first_optimization.propagate_forward(op)

    def propagate_forward(self, op):
        if op.result is not None:
            self.producer[op.result] = op
        dispatch_opt(self, op)

    def emit_operation(self, op):
        if op.returns_bool_result():
            self.bool_boxes[self.getvalue(op.result)] = None
        self._emit_operation(op)

    @specialize.argtype(0)
    def _emit_operation(self, op):
        assert op.getopnum() != rop.CALL_PURE
        changed = False
        orig_op = op
        for i in range(op.numargs()):
            arg = op.getarg(i)
            try:
                value = self.values[arg]
            except KeyError:
                pass
            else:
                self.ensure_imported(value)
                newbox = value.force_box(self)
                if arg is not newbox:
                    if not changed:
                        op = op.clone()
                        changed = True
                    op.setarg(i, newbox)
        self.metainterp_sd.profiler.count(jitprof.Counters.OPT_OPS)
        if op.is_guard():
            self.metainterp_sd.profiler.count(jitprof.Counters.OPT_GUARDS)
            pendingfields = self.pendingfields
            self.pendingfields = None
            if self.replaces_guard and orig_op in self.replaces_guard:
                self.replace_op(self.replaces_guard[orig_op], op)
                del self.replaces_guard[op]
                return
            else:
                guard_op = op.clone()
                op = self.store_final_boxes_in_guard(guard_op, pendingfields)
        elif op.can_raise():
            self.exception_might_have_happened = True
        self._last_emitted_op = orig_op
        self._newoperations.append(op)

    def get_op_replacement(self, op):
        changed = False
        for i, arg in enumerate(op.getarglist()):
            try:
                v = self.values[arg]
            except KeyError:
                pass
            else:
                box = v.get_key_box()
                if box is not arg:
                    if not changed:
                        changed = True
                        op = op.clone()
                    op.setarg(i, box)
        return op

    def replace_op(self, old_op_pos, new_op):
        old_op = self._newoperations[old_op_pos]
        assert old_op.is_guard()
        old_descr = old_op.getdescr()
        new_descr = new_op.getdescr()
        new_descr.copy_all_attributes_from(old_descr)
        self._newoperations[old_op_pos] = new_op

    def store_final_boxes_in_guard(self, op, pendingfields):
        assert pendingfields is not None
        if op.getdescr() is not None:
            descr = op.getdescr()
            assert isinstance(descr, compile.ResumeAtPositionDescr)
        else:
            descr = compile.invent_fail_descr_for_op(op.getopnum(), self)
            op.setdescr(descr)
        assert isinstance(descr, compile.ResumeGuardDescr)
        assert isinstance(op, GuardResOp)
        modifier = resume.ResumeDataVirtualAdder(descr, op,
                                                 self.resumedata_memo)
        try:
            newboxes = modifier.finish(self, pendingfields)
            if len(newboxes) > self.metainterp_sd.options.failargs_limit:
                raise resume.TagOverflow
        except resume.TagOverflow:
            raise compile.giveup()
        descr.store_final_boxes(op, newboxes, self.metainterp_sd)
        #
        if op.getopnum() == rop.GUARD_VALUE:
            if self.getvalue(op.getarg(0)) in self.bool_boxes:
                # Hack: turn guard_value(bool) into guard_true/guard_false.
                # This is done after the operation is emitted to let
                # store_final_boxes_in_guard set the guard_opnum field of the
                # descr to the original rop.GUARD_VALUE.
                constvalue = op.getarg(1).getint()
                if constvalue == 0:
                    opnum = rop.GUARD_FALSE
                elif constvalue == 1:
                    opnum = rop.GUARD_TRUE
                else:
                    raise AssertionError("uh?")
                newop = ResOperation(opnum, [op.getarg(0)], op.result, descr)
                newop.setfailargs(op.getfailargs())
                return newop
            else:
                # a real GUARD_VALUE.  Make it use one counter per value.
                descr.make_a_counter_per_value(op)
        return op

    def make_args_key(self, op):
        n = op.numargs()
        args = [None] * (n + 2)
        for i in range(n):
            arg = self.get_box_replacement(op.getarg(i))
            args[i] = arg
        args[n] = ConstInt(op.getopnum())
        args[n + 1] = op.getdescr()
        return args

    def optimize_default(self, op):
        self.emit_operation(op)

    def constant_fold(self, op):
        argboxes = [self.get_constant_box(op.getarg(i))
                    for i in range(op.numargs())]
        resbox = execute_nonspec(self.cpu, None,
                                 op.getopnum(), argboxes, op.getdescr())
        return resbox.constbox()

    def pure_reverse(self, op):
        import sys
        if self.optpure is None:
            return
        optpure = self.optpure
        if op.getopnum() == rop.INT_ADD:
            arg0 = op.getarg(0)
            arg1 = op.getarg(1)
            optpure.pure(rop.INT_ADD, [arg1, arg0], op.result)
            # Synthesize the reverse op for optimize_default to reuse
            optpure.pure(rop.INT_SUB, [op.result, arg1], arg0)
            optpure.pure(rop.INT_SUB, [op.result, arg0], arg1)
            if isinstance(arg0, ConstInt):
                # invert the constant
                i0 = arg0.getint()
                if i0 == -sys.maxint - 1:
                    return
                inv_arg0 = ConstInt(-i0)
            elif isinstance(arg1, ConstInt):
                # commutative
                i0 = arg1.getint()
                if i0 == -sys.maxint - 1:
                    return
                inv_arg0 = ConstInt(-i0)
                arg1 = arg0
            else:
                return
            optpure.pure(rop.INT_SUB, [arg1, inv_arg0], op.result)
            optpure.pure(rop.INT_SUB, [arg1, op.result], inv_arg0)
            optpure.pure(rop.INT_ADD, [op.result, inv_arg0], arg1)
            optpure.pure(rop.INT_ADD, [inv_arg0, op.result], arg1)

        elif op.getopnum() == rop.INT_SUB:
            arg0 = op.getarg(0)
            arg1 = op.getarg(1)
            optpure.pure(rop.INT_ADD, [op.result, arg1], arg0)
            optpure.pure(rop.INT_SUB, [arg0, op.result], arg1)
            if isinstance(arg1, ConstInt):
                # invert the constant
                i1 = arg1.getint()
                if i1 == -sys.maxint - 1:
                    return
                inv_arg1 = ConstInt(-i1)
                optpure.pure(rop.INT_ADD, [arg0, inv_arg1], op.result)
                optpure.pure(rop.INT_ADD, [inv_arg1, arg0], op.result)
                optpure.pure(rop.INT_SUB, [op.result, inv_arg1], arg0)
                optpure.pure(rop.INT_SUB, [op.result, arg0], inv_arg1)
        elif op.getopnum() == rop.FLOAT_MUL:
            optpure.pure(rop.FLOAT_MUL, [op.getarg(1), op.getarg(0)], op.result)
        elif op.getopnum() == rop.FLOAT_NEG:
            optpure.pure(rop.FLOAT_NEG, [op.result], op.getarg(0))
        elif op.getopnum() == rop.CAST_INT_TO_PTR:
            optpure.pure(rop.CAST_PTR_TO_INT, [op.result], op.getarg(0))
        elif op.getopnum() == rop.CAST_PTR_TO_INT:
            optpure.pure(rop.CAST_INT_TO_PTR, [op.result], op.getarg(0))

    #def optimize_GUARD_NO_OVERFLOW(self, op):
    #    # otherwise the default optimizer will clear fields, which is unwanted
    #    # in this case
    #    self.emit_operation(op)
    # FIXME: Is this still needed?

    def optimize_DEBUG_MERGE_POINT(self, op):
        self.emit_operation(op)

    def optimize_JIT_DEBUG(self, op):
        self.emit_operation(op)

    def optimize_STRGETITEM(self, op):
        indexvalue = self.getvalue(op.getarg(1))
        if indexvalue.is_constant():
            arrayvalue = self.getvalue(op.getarg(0))
            arrayvalue.make_len_gt(MODE_STR, op.getdescr(), indexvalue.box.getint())
        self.optimize_default(op)

    def optimize_UNICODEGETITEM(self, op):
        indexvalue = self.getvalue(op.getarg(1))
        if indexvalue.is_constant():
            arrayvalue = self.getvalue(op.getarg(0))
            arrayvalue.make_len_gt(MODE_UNICODE, op.getdescr(), indexvalue.box.getint())
        self.optimize_default(op)

    # These are typically removed already by OptRewrite, but it can be
    # dissabled and unrolling emits some SAME_AS ops to setup the
    # optimizier state. These needs to always be optimized out.
    def optimize_SAME_AS(self, op):
        self.make_equal_to(op.result, self.getvalue(op.getarg(0)))

    def optimize_MARK_OPAQUE_PTR(self, op):
        value = self.getvalue(op.getarg(0))
        self.optimizer.opaque_pointers[value] = True

dispatch_opt = make_dispatcher_method(Optimizer, 'optimize_',
        default=Optimizer.optimize_default)
