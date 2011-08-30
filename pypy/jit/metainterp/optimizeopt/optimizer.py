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
    _attrs_ = ('box', 'known_class', 'last_guard_index', 'level', 'intbound', 'lenbound')
    last_guard_index = -1

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
            self.make_constant_class(other.known_class, -1)
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
                    

    def force_box(self):
        return self.box

    def get_key_box(self):
        return self.box

    def force_at_end_of_preamble(self, already_forced):
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

    def make_constant_class(self, classbox, opindex):
        assert self.level < LEVEL_KNOWNCLASS
        self.known_class = classbox
        self.level = LEVEL_KNOWNCLASS
        self.last_guard_index = opindex

    def make_nonnull(self, opindex):
        assert self.level < LEVEL_NONNULL
        self.level = LEVEL_NONNULL
        self.last_guard_index = opindex

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

    def propagate_begin_forward(self):
        if self.next_optimization:
            self.next_optimization.propagate_begin_forward()

    def propagate_end_forward(self):
        if self.next_optimization:
            self.next_optimization.propagate_end_forward()

    def propagate_forward(self, op):
        raise NotImplementedError

    def emit_operation(self, op):
        self.next_optimization.propagate_forward(op)

    def test_emittable(self, op):
        return self.is_emittable(op)

    def is_emittable(self, op):
        return self.next_optimization.test_emittable(op)

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

class Optimizer(Optimization):

    def __init__(self, metainterp_sd, loop, optimizations=None, bridge=False):
        self.metainterp_sd = metainterp_sd
        self.cpu = metainterp_sd.cpu
        self.loop = loop
        self.bridge = bridge
        self.values = {}
        self.importable_values = {}
        self.interned_refs = self.cpu.ts.new_ref_dict()
        self.resumedata_memo = resume.ResumeDataLoopMemo(metainterp_sd)
        self.bool_boxes = {}
        self.pure_operations = args_dict()
        self.emitted_pure_operations = {}
        self.producer = {}
        self.pendingfields = []
        self.posponedop = None
        self.exception_might_have_happened = False
        self.quasi_immutable_deps = None
        self.opaque_pointers = {}
        self.newoperations = []
        self.emitting_dissabled = False
        self.emitted_guards = 0        
        if loop is not None:
            self.call_pure_results = loop.call_pure_results

        self.set_optimizations(optimizations)

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
        assert self.posponedop is None
        new = Optimizer(self.metainterp_sd, self.loop)
        optimizations = [o.new() for o in self.optimizations]
        new.set_optimizations(optimizations)
        new.quasi_immutable_deps = self.quasi_immutable_deps
        return new
        
    def produce_potential_short_preamble_ops(self, sb):
        for op in self.emitted_pure_operations:
            if op.getopnum() == rop.GETARRAYITEM_GC_PURE or \
               op.getopnum() == rop.STRGETITEM or \
               op.getopnum() == rop.UNICODEGETITEM:
                if not self.getvalue(op.getarg(1)).is_constant():
                    continue
            sb.add_potential(op)
        for opt in self.optimizations:
            opt.produce_potential_short_preamble_ops(sb)

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

    def getvalue(self, box):
        box = self.getinterned(box)
        try:
            value = self.values[box]
        except KeyError:
            value = self.values[box] = OptValue(box)
        self.ensure_imported(value)
        return value

    def ensure_imported(self, value):
        if not self.emitting_dissabled and value in self.importable_values:
            imp = self.importable_values[value]
            del self.importable_values[value]
            imp.import_value(value)

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
        self.first_optimization.propagate_begin_forward()
        self.i = 0
        while self.i < len(self.loop.operations):
            op = self.loop.operations[self.i]
            self.first_optimization.propagate_forward(op)
            self.i += 1
        self.first_optimization.propagate_end_forward()
        self.loop.operations = self.newoperations
        self.loop.quasi_immutable_deps = self.quasi_immutable_deps
        # accumulate counters
        self.resumedata_memo.update_counters(self.metainterp_sd.profiler)

    def send_extra_operation(self, op):
        self.first_optimization.propagate_forward(op)

    def propagate_forward(self, op):
        self.producer[op.result] = op
        dispatch_opt(self, op)

    def test_emittable(self, op):
        return True

    def emit_operation(self, op):
        if op.returns_bool_result():
            self.bool_boxes[self.getvalue(op.result)] = None
        if self.emitting_dissabled:
            return
        
        for i in range(op.numargs()):
            arg = op.getarg(i)
            if arg in self.values:
                box = self.getvalue(arg).force_box()
                op.setarg(i, box)
        self.metainterp_sd.profiler.count(jitprof.OPT_OPS)
        if op.is_guard():
            self.metainterp_sd.profiler.count(jitprof.OPT_GUARDS)
            self.emitted_guards += 1 # FIXME: can we reuse above counter?
            op = self.store_final_boxes_in_guard(op)
        elif op.can_raise():
            self.exception_might_have_happened = True
        self.newoperations.append(op)

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
                value = self.getvalue(arg)
            except KeyError:
                pass
            else:
                arg = value.get_key_box()
            args[i] = arg
        args[n] = ConstInt(op.getopnum())
        args[n+1] = op.getdescr()
        return args

    def optimize_default(self, op):
        canfold = op.is_always_pure()
        if op.is_ovf():
            self.posponedop = op
            return
        if self.posponedop:
            nextop = op
            op = self.posponedop
            self.posponedop = None
            canfold = nextop.getopnum() == rop.GUARD_NO_OVERFLOW
        else:
            nextop = None

        if canfold:
            for i in range(op.numargs()):
                if self.get_constant_box(op.getarg(i)) is None:
                    break
            else:
                # all constant arguments: constant-fold away
                resbox = self.constant_fold(op)
                # note that INT_xxx_OVF is not done from here, and the
                # overflows in the INT_xxx operations are ignored
                self.make_constant(op.result, resbox)
                return

            # did we do the exact same operation already?
            args = self.make_args_key(op)
            oldop = self.pure_operations.get(args, None)
            if oldop is not None and oldop.getdescr() is op.getdescr():
                assert oldop.getopnum() == op.getopnum()
                self.make_equal_to(op.result, self.getvalue(oldop.result),
                                   True)
                return
            else:
                self.pure_operations[args] = op
                self.emitted_pure_operations[op] = True

        # otherwise, the operation remains
        self.emit_operation(op)
        if nextop:
            self.emit_operation(nextop)

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

    def optimize_CAST_OPAQUE_PTR(self, op):
        value = self.getvalue(op.getarg(0))
        self.opaque_pointers[value] = True
        self.make_equal_to(op.result, value)

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



