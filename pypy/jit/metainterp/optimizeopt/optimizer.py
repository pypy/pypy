from pypy.jit.metainterp import jitprof, resume, compile
from pypy.jit.metainterp.executor import execute_nonspec
from pypy.jit.metainterp.history import BoxInt, BoxFloat, Const, ConstInt, REF
from pypy.jit.metainterp.optimizeopt.intutils import IntBound, IntUnbounded, \
                                                     ImmutableIntUnbounded, \
                                                     IntLowerBound, MININT, MAXINT
from pypy.jit.metainterp.optimizeopt.util import (make_dispatcher_method,
    args_dict)
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp.typesystem import llhelper, oohelper
from pypy.tool.pairtype import extendabletype
from pypy.rlib.debug import debug_start, debug_stop, debug_print
from pypy.rlib.objectmodel import specialize

LEVEL_UNKNOWN    = '\x00'
LEVEL_NONNULL    = '\x01'
LEVEL_KNOWNCLASS = '\x02'     # might also mean KNOWNARRAYDESCR, for arrays
LEVEL_CONSTANT   = '\x03'

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

class OptValue(object):
    __metaclass__ = extendabletype
    _attrs_ = ('box', 'known_class', 'last_guard', 'level', 'intbound', 'lenbound')
    last_guard = None

    level = LEVEL_UNKNOWN
    known_class = None
    intbound = ImmutableIntUnbounded()
    lenbound = None

    def __init__(self, box, level=None, known_class=None, intbound=None):
        self.box = box
        if level is not None:
            self.level = level
        self.known_class = known_class
        if intbound:
            self.intbound = intbound
        else:
            if isinstance(box, BoxInt):
                self.intbound = IntBound(MININT, MAXINT)
            else:
                self.intbound = IntUnbounded()

        if isinstance(box, Const):
            self.make_constant(box)
        # invariant: box is a Const if and only if level == LEVEL_CONSTANT

    def make_len_gt(self, mode, descr, val):
        if self.lenbound:
            assert self.lenbound.mode == mode
            assert self.lenbound.descr == descr
            self.lenbound.bound.make_gt(IntBound(val, val))
        else:
            self.lenbound = LenBound(mode, descr, IntLowerBound(val + 1))

    def make_guards(self, box):
        guards = []
        if self.level == LEVEL_CONSTANT:
            op = ResOperation(rop.GUARD_VALUE, [box, self.box], None)
            guards.append(op)
        elif self.level == LEVEL_KNOWNCLASS:
            op = ResOperation(rop.GUARD_NONNULL, [box], None)
            guards.append(op)
            op = ResOperation(rop.GUARD_CLASS, [box, self.known_class], None)
            guards.append(op)
        else:
            if self.level == LEVEL_NONNULL:
                op = ResOperation(rop.GUARD_NONNULL, [box], None)
                guards.append(op)
            self.intbound.make_guards(box, guards)
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

    def import_from(self, other, optimizer):
        assert self.level <= LEVEL_NONNULL
        if other.level == LEVEL_CONSTANT:
            self.make_constant(other.get_key_box())
            optimizer.turned_constant(self)
        elif other.level == LEVEL_KNOWNCLASS:
            self.make_constant_class(other.known_class, None)
        else:
            if other.level == LEVEL_NONNULL:
                self.ensure_nonnull()
            self.intbound.intersect(other.intbound)
            if other.lenbound:
                if self.lenbound:
                    assert other.lenbound.mode == self.lenbound.mode
                    assert other.lenbound.descr == self.lenbound.descr
                    self.lenbound.bound.intersect(other.lenbound.bound)
                else:
                    self.lenbound = other.lenbound.clone()


    def force_box(self, optforce):
        return self.box

    def get_key_box(self):
        return self.box

    def force_at_end_of_preamble(self, already_forced, optforce):
        return self

    def get_args_for_fail(self, modifier):
        pass

    def make_virtual_info(self, modifier, fieldnums):
        #raise NotImplementedError # should not be called on this level
        assert fieldnums is None
        return modifier.make_not_virtual(self)

    def is_constant(self):
        return self.level == LEVEL_CONSTANT

    def is_null(self):
        if self.is_constant():
            box = self.box
            assert isinstance(box, Const)
            return not box.nonnull()
        return False

    def make_constant(self, constbox):
        """Replace 'self.box' with a Const box."""
        assert isinstance(constbox, Const)
        self.box = constbox
        self.level = LEVEL_CONSTANT

        if isinstance(constbox, ConstInt):
            val = constbox.getint()
            self.intbound = IntBound(val, val)
        else:
            self.intbound = IntUnbounded()

    def get_constant_class(self, cpu):
        level = self.level
        if level == LEVEL_KNOWNCLASS:
            return self.known_class
        elif level == LEVEL_CONSTANT:
            return cpu.ts.cls_of_box(self.box)
        else:
            return None

    def make_constant_class(self, classbox, guardop):
        assert self.level < LEVEL_KNOWNCLASS
        self.known_class = classbox
        self.level = LEVEL_KNOWNCLASS
        self.last_guard = guardop

    def make_nonnull(self, guardop):
        assert self.level < LEVEL_NONNULL
        self.level = LEVEL_NONNULL
        self.last_guard = guardop

    def is_nonnull(self):
        level = self.level
        if level == LEVEL_NONNULL or level == LEVEL_KNOWNCLASS:
            return True
        elif level == LEVEL_CONSTANT:
            box = self.box
            assert isinstance(box, Const)
            return box.nonnull()
        elif self.intbound:
            if self.intbound.known_gt(IntBound(0, 0)) or \
               self.intbound.known_lt(IntBound(0, 0)):
                return True
            else:
                return False
        else:
            return False

    def ensure_nonnull(self):
        if self.level < LEVEL_NONNULL:
            self.level = LEVEL_NONNULL

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

    def getitem(self, index):
        raise NotImplementedError

    def getlength(self):
        raise NotImplementedError

    def setitem(self, index, value):
        raise NotImplementedError


class ConstantValue(OptValue):
    def __init__(self, box):
        self.make_constant(box)

    def __repr__(self):
        return 'Constant(%r)' % (self.box,)

CONST_0      = ConstInt(0)
CONST_1      = ConstInt(1)
CVAL_ZERO    = ConstantValue(CONST_0)
CVAL_ZERO_FLOAT = ConstantValue(Const._new(0.0))
CVAL_UNINITIALIZED_ZERO = ConstantValue(CONST_0)
llhelper.CVAL_NULLREF = ConstantValue(llhelper.CONST_NULL)
oohelper.CVAL_NULLREF = ConstantValue(oohelper.CONST_NULL)

class Optimization(object):
    next_optimization = None

    def __init__(self):
        pass # make rpython happy

    def propagate_forward(self, op):
        raise NotImplementedError

    def emit_operation(self, op):
        self.next_optimization.propagate_forward(op)

    # FIXME: Move some of these here?
    def getvalue(self, box):
        return self.optimizer.getvalue(box)

    def make_constant(self, box, constbox):
        return self.optimizer.make_constant(box, constbox)

    def make_constant_int(self, box, intconst):
        return self.optimizer.make_constant_int(box, intconst)

    def make_equal_to(self, box, value):
        return self.optimizer.make_equal_to(box, value)

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
        op = ResOperation(opnum, args, result)
        key = self.optimizer.make_args_key(op)
        if key not in self.optimizer.pure_operations:
            self.optimizer.pure_operations[key] = op

    def has_pure_result(self, opnum, args, descr):
        op = ResOperation(opnum, args, None, descr)
        key = self.optimizer.make_args_key(op)
        op = self.optimizer.pure_operations.get(key, None)
        if op is None:
            return False
        return op.getdescr() is descr

    def setup(self):
        pass

    def turned_constant(self, value):
        pass

    def force_at_end_of_preamble(self):
        pass

    # It is too late to force stuff here, it must be done in force_at_end_of_preamble
    def new(self):
        raise NotImplementedError

    # Called after last operation has been propagated to flush out any posponed ops
    def flush(self):
        pass

    def produce_potential_short_preamble_ops(self, potential_ops):
        pass

    def forget_numberings(self, box):
        self.optimizer.forget_numberings(box)

class Optimizer(Optimization):

    def __init__(self, metainterp_sd, loop, optimizations=None, bridge=False):
        self.metainterp_sd = metainterp_sd
        self.cpu = metainterp_sd.cpu
        self.loop = loop
        self.bridge = bridge
        self.values = {}
        self.interned_refs = self.cpu.ts.new_ref_dict()
        self.resumedata_memo = resume.ResumeDataLoopMemo(metainterp_sd)
        self.bool_boxes = {}
        self.pure_operations = args_dict()
        self.producer = {}
        self.pendingfields = []
        self.posponedop = None
        self.exception_might_have_happened = False
        self.quasi_immutable_deps = None
        self.opaque_pointers = {}
        self.replaces_guard = {}
        self.newoperations = []
        self.optimizer = self
        self.optpure = None
        self.optearlyforce = None
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
                o.setup()
        else:
            optimizations = []
            self.first_optimization = self

        self.optimizations  = optimizations

    def force_at_end_of_preamble(self):
        for o in self.optimizations:
            o.force_at_end_of_preamble()

    def flush(self):
        for o in self.optimizations:
            o.flush()
        assert self.posponedop is None

    def new(self):
        new = Optimizer(self.metainterp_sd, self.loop)
        return self._new(new)

    def _new(self, new):
        assert self.posponedop is None
        optimizations = [o.new() for o in self.optimizations]
        new.set_optimizations(optimizations)
        new.quasi_immutable_deps = self.quasi_immutable_deps
        return new

    def produce_potential_short_preamble_ops(self, sb):
        raise NotImplementedError('This is implemented in unroll.UnrollableOptimizer')

    def turned_constant(self, value):
        for o in self.optimizations:
            o.turned_constant(value)

    def forget_numberings(self, virtualbox):
        self.metainterp_sd.profiler.count(jitprof.OPT_FORCINGS)
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
        else:
            return box

    @specialize.argtype(0)
    def getvalue(self, box):
        box = self.getinterned(box)
        try:
            value = self.values[box]
        except KeyError:
            value = self.values[box] = OptValue(box)
        self.ensure_imported(value)
        return value

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

    def make_equal_to(self, box, value, replace=False):
        assert isinstance(value, OptValue)
        assert replace or box not in self.values
        self.values[box] = value

    def make_constant(self, box, constbox):
        self.make_equal_to(box, ConstantValue(constbox))

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

    def propagate_all_forward(self):
        self.exception_might_have_happened = self.bridge
        self.newoperations = []
        for op in self.loop.operations:
            self.first_optimization.propagate_forward(op)
        self.loop.operations = self.newoperations
        self.loop.quasi_immutable_deps = self.quasi_immutable_deps
        # accumulate counters
        self.resumedata_memo.update_counters(self.metainterp_sd.profiler)

    def send_extra_operation(self, op):
        self.first_optimization.propagate_forward(op)

    def propagate_forward(self, op):
        self.producer[op.result] = op
        dispatch_opt(self, op)

    def emit_operation(self, op):
        if op.returns_bool_result():
            self.bool_boxes[self.getvalue(op.result)] = None
        self._emit_operation(op)

    @specialize.argtype(0)
    def _emit_operation(self, op):
        for i in range(op.numargs()):
            arg = op.getarg(i)
            try:
                value = self.values[arg]
            except KeyError:
                pass
            else:
                self.ensure_imported(value)
                op.setarg(i, value.force_box(self))
        self.metainterp_sd.profiler.count(jitprof.OPT_OPS)
        if op.is_guard():
            self.metainterp_sd.profiler.count(jitprof.OPT_GUARDS)
            if self.replaces_guard and op in self.replaces_guard:
                self.replace_op(self.replaces_guard[op], op)
                del self.replaces_guard[op]
                return
            else:
                op = self.store_final_boxes_in_guard(op)
        elif op.can_raise():
            self.exception_might_have_happened = True
        self.newoperations.append(op)

    def replace_op(self, old_op, new_op):
        # XXX: Do we want to cache indexes to prevent search?
        i = len(self.newoperations) 
        while i > 0:
            i -= 1
            if self.newoperations[i] is old_op:
                self.newoperations[i] = new_op
                break
        else:
            assert False

    def store_final_boxes_in_guard(self, op):
        descr = op.getdescr()
        assert isinstance(descr, compile.ResumeGuardDescr)
        modifier = resume.ResumeDataVirtualAdder(descr, self.resumedata_memo)
        newboxes = modifier.finish(self.values, self.pendingfields)
        if len(newboxes) > self.metainterp_sd.options.failargs_limit: # XXX be careful here
            compile.giveup()
        descr.store_final_boxes(op, newboxes)
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
            arg = op.getarg(i)
            try:
                value = self.values[arg]
            except KeyError:
                pass
            else:
                arg = value.get_key_box()
            args[i] = arg
        args[n] = ConstInt(op.getopnum())
        args[n + 1] = op.getdescr()
        return args

    def optimize_default(self, op):
        self.emit_operation(op)

    def remember_emitting_pure(self, op):
        pass

    def constant_fold(self, op):
        argboxes = [self.get_constant_box(op.getarg(i))
                    for i in range(op.numargs())]
        resbox = execute_nonspec(self.cpu, None,
                                 op.getopnum(), argboxes, op.getdescr())
        return resbox.constbox()

    #def optimize_GUARD_NO_OVERFLOW(self, op):
    #    # otherwise the default optimizer will clear fields, which is unwanted
    #    # in this case
    #    self.emit_operation(op)
    # FIXME: Is this still needed?

    def optimize_DEBUG_MERGE_POINT(self, op):
        self.emit_operation(op)

    def optimize_GETARRAYITEM_GC_PURE(self, op):
        indexvalue = self.getvalue(op.getarg(1))
        if indexvalue.is_constant():
            arrayvalue = self.getvalue(op.getarg(0))
            arrayvalue.make_len_gt(MODE_ARRAY, op.getdescr(), indexvalue.box.getint())
        self.optimize_default(op)

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




dispatch_opt = make_dispatcher_method(Optimizer, 'optimize_',
        default=Optimizer.optimize_default)



