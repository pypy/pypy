from rpython.jit.metainterp import jitprof, resume, compile
from rpython.jit.metainterp.executor import execute_nonspec_const
from rpython.jit.metainterp.logger import LogOperations
from rpython.jit.metainterp.history import Const, ConstInt, REF, ConstPtr
from rpython.jit.metainterp.optimizeopt.intutils import IntBound,\
     IntLowerBound, MININT, MAXINT, IntUnbounded, ConstIntBound
from rpython.jit.metainterp.optimizeopt.util import make_dispatcher_method
from rpython.jit.metainterp.resoperation import rop, ResOperation,\
     AbstractResOp, AbstractInputArg, GuardResOp, AbstractValue
from rpython.jit.metainterp.typesystem import llhelper
from rpython.tool.pairtype import extendabletype
from rpython.rlib.debug import debug_print
from rpython.rlib.objectmodel import specialize, we_are_translated

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


## class OptInfo(object):

##     def getlevel(self):
##         return self._tag & 0x3

##     def setlevel(self, level):
##         self._tag = (self._tag & (~0x3)) | level

##     def import_from(self, other, optimizer):
##         if self.getlevel() == LEVEL_CONSTANT:
##             assert other.getlevel() == LEVEL_CONSTANT
##             assert other.box.same_constant(self.box)
##             return
##         assert self.getlevel() <= LEVEL_NONNULL
##         if other.getlevel() == LEVEL_CONSTANT:
##             self.make_constant(other.get_key_box())
##         elif other.getlevel() == LEVEL_KNOWNCLASS:
##             self.make_constant_class(None, other.get_known_class())
##         else:
##             if other.getlevel() == LEVEL_NONNULL:
##                 self.ensure_nonnull()

##     def make_guards(self, box):
##         if self.getlevel() == LEVEL_CONSTANT:
##             op = ResOperation(rop.GUARD_VALUE, [box, self.box], None)
##             return [op]
##         return []

##     def copy_from(self, other_value):
##         assert isinstance(other_value, OptValue)
##         self.box = other_value.box
##         self._tag = other_value._tag

##     def force_box(self, optforce):
##         xxx
##         return self.box

##     def force_at_end_of_preamble(self, already_forced, optforce):
##         return self

##     # visitor API

##     def visitor_walk_recursive(self, visitor):
##         pass

##     @specialize.argtype(1)
##     def visitor_dispatch_virtual_type(self, visitor):
##         if self.is_virtual():
##             return self._visitor_dispatch_virtual_type(visitor)
##         else:
##             return visitor.visit_not_virtual(self)

##     @specialize.argtype(1)
##     def _visitor_dispatch_virtual_type(self, visitor):
##         assert 0, "unreachable"

##     def is_constant(self):
##         return self.getlevel() == LEVEL_CONSTANT

##     def is_null(self):
##         if self.is_constant():
##             box = self.box
##             assert isinstance(box, Const)
##             return not box.nonnull()
##         return False

##     def same_value(self, other):
##         if not other:
##             return False
##         if self.is_constant() and other.is_constant():
##             return self.box.same_constant(other.box)
##         return self is other

##     def is_nonnull(self):
##         level = self.getlevel()
##         if level == LEVEL_NONNULL or level == LEVEL_KNOWNCLASS:
##             return True
##         elif level == LEVEL_CONSTANT:
##             box = self.box
##             assert isinstance(box, Const)
##             return box.nonnull()
##         else:
##             return False

##     def ensure_nonnull(self):
##         if self.getlevel() < LEVEL_NONNULL:
##             self.setlevel(LEVEL_NONNULL)

##     def get_constant_int(self):
##         assert self.is_constant()
##         box = self.box
##         assert isinstance(box, ConstInt)
##         return box.getint()

##     def is_virtual(self):
##         return False # overwridden in VirtualInfo

##     def is_forced_virtual(self):
##         return False

##     def getfield(self, ofs, default):
##         raise NotImplementedError

##     def setfield(self, ofs, value):
##         raise NotImplementedError

##     def getlength(self):
##         raise NotImplementedError

##     def getitem(self, index):
##         raise NotImplementedError

##     def setitem(self, index, value):
##         raise NotImplementedError

##     def getitem_raw(self, offset, length, descr):
##         raise NotImplementedError

##     def setitem_raw(self, offset, length, descr, value):
##         raise NotImplementedError

##     def getinteriorfield(self, index, ofs, default):
##         raise NotImplementedError

##     def setinteriorfield(self, index, ofs, value):
##         raise NotImplementedError

##     def get_missing_null_value(self):
##         raise NotImplementedError    # only for VArrayValue

##     def make_constant(self, constbox):
##         """Replace 'self.box' with a Const box."""
##         assert isinstance(constbox, Const)
##         self.box = constbox
##         self.setlevel(LEVEL_CONSTANT)

##     def get_last_guard(self, optimizer):
##         return None

##     def get_known_class(self):
##         return None

##     def getlenbound(self):
##         return None

##     def getintbound(self):
##         return None

##     def get_constant_class(self, cpu):
##         return None


class PtrOptInfo(AbstractValue):
    _attrs_ = ('_tag', 'known_class', 'last_guard_pos', 'lenbound')
    is_info_class = True

    _tag = 0
    known_class = None
    last_guard_pos = -1
    lenbound = None

    #def __init__(self, level=None, known_class=None, intbound=None):
    #    OptValue.__init__(self, box, level, None, intbound)
    #    if not isinstance(box, Const):
    #        self.known_class = known_class

    def getlevel(self):
        return self._tag & 0x3

    def setlevel(self, level):
        self._tag = (self._tag & (~0x3)) | level

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

## class IntOptInfo(OptInfo):
##     _attrs_ = ('intbound',)

##     def __init__(self, level=LEVEL_UNKNOWN, known_class=None, intbound=None):
##         OptInfo.__init__(self, level, None, None)
##         if intbound:
##             self.intbound = intbound
##         else:
##             self.intbound = IntBound(MININT, MAXINT)

##     def copy_from(self, other_value):
##         assert isinstance(other_value, IntOptValue)
##         self.box = other_value.box
##         self.intbound = other_value.intbound
##         self._tag = other_value._tag

##     def make_constant(self, constbox):
##         """Replace 'self.box' with a Const box."""
##         assert isinstance(constbox, ConstInt)
##         self.box = constbox
##         self.setlevel(LEVEL_CONSTANT)
##         val = constbox.getint()
##         self.intbound = IntBound(val, val)

##     def is_nonnull(self):
##         if OptValue.is_nonnull(self):
##             return True
##         if self.intbound:
##             if self.intbound.known_gt(IntBound(0, 0)) or \
##                self.intbound.known_lt(IntBound(0, 0)):
##                 return True
##         return False

##     def make_nonnull(self, optimizer):
##         assert self.getlevel() < LEVEL_NONNULL
##         self.setlevel(LEVEL_NONNULL)

##     def import_from(self, other, optimizer):
##         OptValue.import_from(self, other, optimizer)
##         if self.getlevel() != LEVEL_CONSTANT:
##             if other.getintbound() is not None: # VRawBufferValue
##                 self.intbound.intersect(other.getintbound())

##     def make_guards(self, box):
##         guards = []
##         level = self.getlevel()
##         if level == LEVEL_CONSTANT:
##             op = ResOperation(rop.GUARD_VALUE, [box, self.box], None)
##             guards.append(op)
##         elif level == LEVEL_KNOWNCLASS:
##             op = ResOperation(rop.GUARD_NONNULL, [box], None)
##             guards.append(op)
##         else:
##             if level == LEVEL_NONNULL:
##                 op = ResOperation(rop.GUARD_NONNULL, [box], None)
##                 guards.append(op)
##             self.intbound.make_guards(box, guards)
##         return guards

##     def getintbound(self):
##         return self.intbound

##     def get_last_guard(self, optimizer):
##         return None

##     def get_known_class(self):
##         return None

##     def getlenbound(self):
##         return None


CONST_0      = ConstInt(0)
CONST_1      = ConstInt(1)
CONST_ZERO_FLOAT = Const._new(0.0)
llhelper.CONST_NULLREF = llhelper.CONST_NULL
REMOVED = AbstractResOp()

INFO_NULL = 0
INFO_NONNULL = 1
INFO_UNKNOWN = 2

class Optimization(object):
    next_optimization = None

    def __init__(self):
        pass # make rpython happy

    def propagate_forward(self, op):
        raise NotImplementedError

    def emit_operation(self, op):
        self.last_emitted_operation = op
        self.next_optimization.propagate_forward(op)

    def getintbound(self, op):#, create=True):
        assert op.type == 'i'
        op = self.get_box_replacement(op)
        if isinstance(op, ConstInt):
            return ConstIntBound(op.getint())
        fw = op.get_forwarded()
        if isinstance(fw, IntBound):
            return fw
        assert fw is None
        assert op.type == 'i'
        intbound = IntUnbounded()
        op.set_forwarded(intbound)
        return intbound

    def getnullness(self, op):
        if op.type == 'i':
            return self.getintbound(op).getnullness()
        xxxx

    def getptrinfo(self, op):
        assert op.type == 'r'
        op = self.get_box_replacement(op)
        assert op.type == 'r'
        if isinstance(op, ConstPtr):
            xxx
        fw = op.get_forwarded()
        if fw is not None:
            assert isinstance(fw, PtrOptInfo)
            return fw
        ptrinfo = PtrOptInfo()
        op.set_forwarded(ptrinfo)
        return ptrinfo

    def get_box_replacement(self, op):
        return self.optimizer.get_box_replacement(op)

    def getlastop(self):
        return self.optimizer._last_emitted_op

    def replace_op_with(self, op, newopnum, args=None, descr=None):
        return self.optimizer.replace_op_with(op, newopnum, args, descr)

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
        self.logops = LogOperations(metainterp_sd, False)
        self.interned_refs = self.cpu.ts.new_ref_dict()
        self.interned_ints = {}
        self.resumedata_memo = resume.ResumeDataLoopMemo(metainterp_sd)
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

    ## def getinfo(self, op, create=False):
    ##     xxx
    ##     yyy

    ##     XXX
    ##     box = self.getinterned(box)
    ##     try:
    ##         value = self.values[box]
    ##     except KeyError:
    ##         if box.type == "r":
    ##             value = self.values[box] = PtrOptValue(box)
    ##         elif box.type == "i":
    ##             value = self.values[box] = IntOptValue(box)
    ##         else:
    ##             assert box.type == "f"
    ##             value = self.values[box] = OptValue(box)
    ##     self.ensure_imported(value)
    ##     return value

    def get_box_replacement(self, op):
        orig_op = op
        while (op.get_forwarded() is not None and
               not op.get_forwarded().is_info_class):
            op = op.get_forwarded()
        if op is not orig_op:
            orig_op.set_forwarded(op)
        return op

    def force_box(self, op):
        return self.get_box_replacement(op)

    def ensure_imported(self, value):
        pass

    def get_constant_box(self, box):
        box = self.get_box_replacement(box)
        if isinstance(box, Const):
            return box
        #self.ensure_imported(value)

    def get_newoperations(self):
        self.flush()
        return self._newoperations

    def clear_newoperations(self):
        self._newoperations = []

    def make_equal_to(self, box, value):
        assert isinstance(value, OptValue)
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

    def replace_op_with(self, op, newopnum, args=None, descr=None):
        newop = op.copy_and_change(newopnum, args, descr)
        if newop.type != 'v':
            assert op.get_forwarded() is None  #XXX
            op.set_forwarded(newop)
        return newop

    def make_constant(self, box, constbox):
        assert isinstance(constbox, ConstInt)
        box = self.get_box_replacement(box)
        if not we_are_translated():    # safety-check
            if box.get_forwarded() is not None:
                assert box.get_forwarded().contains(constbox.getint())
        if box.is_constant():
            return
        box.set_forwarded(constbox)

    def make_constant_int(self, box, intvalue):
        self.make_constant(box, ConstInt(intvalue))

    def new_ptr_box(self):
        xxx
        return self.cpu.ts.BoxRef()

    def new_box(self, fieldofs):
        xxx
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
        xxx
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
            self._last_emitted_op = None
            self.first_optimization.propagate_forward(op)
        self.loop.operations = self.get_newoperations()
        self.loop.quasi_immutable_deps = self.quasi_immutable_deps
        # accumulate counters
        self.resumedata_memo.update_counters(self.metainterp_sd.profiler)

    def send_extra_operation(self, op):
        self.first_optimization.propagate_forward(op)

    def propagate_forward(self, op):
        dispatch_opt(self, op)

    def emit_operation(self, op):
        if op.returns_bool_result():
            self.getintbound(op).make_bool()
        self._emit_operation(op)

    @specialize.argtype(0)
    def _emit_operation(self, op):
        assert not op.is_call_pure()
        orig_op = op
        op = self.replace_op_with(op, op.getopnum())
        for i in range(op.numargs()):
            arg = self.force_box(op.getarg(i))
            #self.ensure_imported(value)
            #    newbox = value.force_box(self)
            op.setarg(i, arg)
        self.metainterp_sd.profiler.count(jitprof.Counters.OPT_OPS)
        if op.is_guard():
            self.metainterp_sd.profiler.count(jitprof.Counters.OPT_GUARDS)
            pendingfields = self.pendingfields
            self.pendingfields = None
            if self.replaces_guard and orig_op in self.replaces_guard:
                self.replace_guard_op(self.replaces_guard[orig_op], op)
                del self.replaces_guard[orig_op]
                return
            else:
                guard_op = self.replace_op_with(op, op.getopnum())
                op = self.store_final_boxes_in_guard(guard_op, pendingfields)
        elif op.can_raise():
            self.exception_might_have_happened = True
        self._last_emitted_op = op
        self._newoperations.append(op)

    def get_op_replacement(self, op):
        # XXX this is wrong
        xxx
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
                        op = op.copy_and_change(op.getopnum())
                    op.setarg(i, box)
        return op

    def replace_guard_op(self, old_op_pos, new_op):
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
            if (newboxes is not None and
                len(newboxes) > self.metainterp_sd.options.failargs_limit):
                raise resume.TagOverflow
        except resume.TagOverflow:
            raise compile.giveup()
        descr.store_final_boxes(op, newboxes, self.metainterp_sd)
        #
        if op.getopnum() == rop.GUARD_VALUE and 0: # XXX
            val = self.getvalue(op.getarg(0))
            if val in self.bool_boxes:
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
                newop = self.replace_op_with(op, opnum, [op.getarg(0)], descr)
                newop.setfailargs(op.getfailargs())
                return newop
            else:
                # a real GUARD_VALUE.  Make it use one counter per value.
                descr.make_a_counter_per_value(op)
        return op

    def make_args_key(self, opnum, arglist, descr):
        n = len(arglist)
        args = [None] * (n + 2)
        for i in range(n):
            arg = self.get_box_replacement(arglist[i])
            args[i] = arg
        args[n] = ConstInt(opnum)
        args[n + 1] = descr
        return args

    def optimize_default(self, op):
        self.emit_operation(op)

    def constant_fold(self, op):
        argboxes = [self.get_constant_box(op.getarg(i))
                    for i in range(op.numargs())]
        return execute_nonspec_const(self.cpu, None,
                                       op.getopnum(), argboxes,
                                       op.getdescr(), op.type)

    def pure_reverse(self, op):
        if self.optpure is None:
            return
        optpure = self.optpure
        if op.getopnum() == rop.INT_ADD:
            optpure.pure(rop.INT_ADD, [op.getarg(1), op.getarg(0)], op)
            # Synthesize the reverse op for optimize_default to reuse
            optpure.pure(rop.INT_SUB, [op, op.getarg(1)], op.getarg(0))
            optpure.pure(rop.INT_SUB, [op, op.getarg(0)], op.getarg(1))
        elif op.getopnum() == rop.INT_SUB:
            optpure.pure(rop.INT_ADD, [op, op.getarg(1)], op.getarg(0))
            optpure.pure(rop.INT_SUB, [op.getarg(0), op], op.getarg(1))
        elif op.getopnum() == rop.FLOAT_MUL:
            optpure.pure(rop.FLOAT_MUL, [op.getarg(1), op.getarg(0)], op)
        elif op.getopnum() == rop.FLOAT_NEG:
            optpure.pure(rop.FLOAT_NEG, [op], op.getarg(0))
        elif op.getopnum() == rop.CAST_INT_TO_PTR:
            optpure.pure(rop.CAST_PTR_TO_INT, [op], op.getarg(0))
        elif op.getopnum() == rop.CAST_PTR_TO_INT:
            optpure.pure(rop.CAST_INT_TO_PTR, [op], op.getarg(0))

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
    def optimize_SAME_AS_I(self, op):
        self.make_equal_to(op, self.getvalue(op.getarg(0)))
    optimize_SAME_AS_R = optimize_SAME_AS_I
    optimize_SAME_AS_F = optimize_SAME_AS_I

    def optimize_MARK_OPAQUE_PTR(self, op):
        value = self.getvalue(op.getarg(0))
        self.optimizer.opaque_pointers[value] = True

dispatch_opt = make_dispatcher_method(Optimizer, 'optimize_',
        default=Optimizer.optimize_default)
