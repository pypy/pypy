from rpython.jit.metainterp.optimizeopt.optimizer import (
    Optimization, OptimizationResult, REMOVED)
from rpython.jit.metainterp.resoperation import rop, OpHelpers, AbstractResOp,\
     ResOperation
from rpython.jit.metainterp.optimizeopt.util import (
    make_dispatcher_method, have_dispatcher_method, get_box_replacement)
from rpython.jit.metainterp.optimizeopt.shortpreamble import PreambleOp
from rpython.jit.metainterp.optimize import SpeculativeError


class DefaultOptimizationResult(OptimizationResult):
    def __init__(self, opt, op, save, nextop):
        OptimizationResult.__init__(self, opt, op)
        self.save = save
        self.nextop = nextop

    def callback(self):
        self._callback(self.op, self.save, self.nextop)

    def _callback(self, op, save, nextop):
        if rop.returns_bool_result(op.opnum):
            self.opt.getintbound(op).make_bool()
        if save:
            recentops = self.opt.getrecentops(op.getopnum())
            recentops.add(op)
        if nextop:
            self.opt.emit_extra(nextop)


class CallPureOptimizationResult(OptimizationResult):
    def callback(self):
        self.opt.call_pure_positions.append(
            len(self.opt.optimizer._newoperations) - 1)


class RecentPureOps(object):
    def __init__(self, limit=16):
        self.lst = [None] * limit
        self.next_index = 0

    def add(self, op):
        assert isinstance(op, AbstractResOp)
        next_index = self.next_index
        new = next_index + 1
        if new == len(self.lst):
            new = 0
        self.next_index = new
        self.lst[next_index] = op

    def force_preamble_op(self, opt, op, i):
        if not isinstance(op, PreambleOp):
            return op
        op = opt.force_op_from_preamble(op)
        self.lst[i] = op
        return op

    def lookup1(self, opt, box0, descr):
        for i in range(len(self.lst)):
            op = self.lst[i]
            if op is None:
                break
            if box0.same_box(get_box_replacement(op.getarg(0))) and op.getdescr() is descr:
                op = self.force_preamble_op(opt, op, i)
                return get_box_replacement(op)
        return None

    def lookup2(self, opt, box0, box1, descr):
        for i in range(len(self.lst)):
            op = self.lst[i]
            if op is None:
                break
            if (box0.same_box(get_box_replacement(op.getarg(0))) and
                box1.same_box(get_box_replacement(op.getarg(1))) and
                op.getdescr() is descr):
                op = self.force_preamble_op(opt, op, i)
                return get_box_replacement(op)
        return None

    def lookup(self, optimizer, op):
        numargs = op.numargs()
        if numargs == 1:
            return self.lookup1(optimizer,
                                get_box_replacement(op.getarg(0)),
                                op.getdescr())
        elif numargs == 2:
            return self.lookup2(optimizer,
                                get_box_replacement(op.getarg(0)),
                                get_box_replacement(op.getarg(1)),
                                op.getdescr())
        else:
            assert False


class OptPure(Optimization):
    def __init__(self):
        self.postponed_op = None
        self._pure_operations = [None] * (rop._ALWAYS_PURE_LAST -
                                          rop._ALWAYS_PURE_FIRST)
        self.call_pure_positions = []
        self.extra_call_pure = []
        self.known_result_call_pure = []

    def propagate_forward(self, op):
        return dispatch_opt(self, op)

    def optimize_default(self, op):
        canfold = rop.is_always_pure(op.opnum)
        ovf = False
        if rop.is_ovf(op.opnum):
            self.postponed_op = op
            return
        if self.postponed_op:
            nextop = op
            op = self.postponed_op
            self.postponed_op = None
            canfold = nextop.getopnum() == rop.GUARD_NO_OVERFLOW
            ovf = True
        else:
            nextop = None

        save = False
        if canfold:
            for i in range(op.numargs()):
                if self.get_constant_box(op.getarg(i)) is None:
                    break
            else:
                # all constant arguments: constant-fold away
                resbox = self.optimizer.constant_fold(op)
                # note that INT_xxx_OVF is not done from here, and the
                # overflows in the INT_xxx operations are ignored
                self.optimizer.make_constant(op, resbox)
                return

            # did we do the exact same operation already?
            recentops = self.getrecentops(op.getopnum(), create=False)
            save = True
            if recentops is not None:
                oldop = recentops.lookup(self.optimizer, op)
                if oldop is not None and self._can_reuse_oldop(
                            recentops, oldop, op, ovf):
                    self.optimizer.make_equal_to(op, oldop)
                    return

        # otherwise, the operation remains
        if nextop is None and not save and not rop.returns_bool_result(op.getopnum()):
            # for this case DefaultOptimizationResult would do nothing
            return self.emit(op)
        return self.emit_result(DefaultOptimizationResult(self, op, save, nextop))

    def _can_reuse_oldop(self, recentops, oldop, op, ovf):
        if ovf:
            # careful! this is an ovf operation. so we can only
            # re-use the result of a prior ovf operation, but not a
            # regular int_... up, because that might have
            # overflowed (the other direction is fine). therefore
            # we need to check that the previous op and the current
            # op have the same opnum.
            return isinstance(oldop, AbstractResOp) and oldop.opnum == op.opnum
        return True

    def getrecentops(self, opnum, create=True):
        if rop._OVF_FIRST <= opnum <= rop._OVF_LAST:
            opnum = opnum - rop._OVF_FIRST
        else:
            opnum = opnum - rop._ALWAYS_PURE_FIRST
        assert 0 <= opnum < len(self._pure_operations)
        recentops = self._pure_operations[opnum]
        if recentops is None and create:
            length = self.optimizer.jitdriver_sd.warmstate.pureop_historylength
            self._pure_operations[opnum] = recentops = RecentPureOps(length)
        return recentops

    def optimize_call_pure(self, op, start_index=0):
        # Step 1: check if all arguments are constant
        for i in range(start_index, op.numargs()):
            self.optimizer.force_box(op.getarg(i))
            # XXX hack to ensure that virtuals that are
            #     constant are presented that way
        result = self._can_optimize_call_pure(op, start_index=start_index)
        if result is not None:
            # this removes a CALL_PURE with all constant arguments.
            self.make_constant(op, result)
            self.last_emitted_operation = REMOVED
            return

        # Step 2: check if all arguments are the same as a previous
        # CALL_PURE.
        for pos in self.call_pure_positions:
            old_op = self.optimizer._newoperations[pos]
            if self.optimize_call_pure_old(op, old_op, start_index):
                return
        if self.extra_call_pure:
            for i, old_op in enumerate(self.extra_call_pure):
                if self.optimize_call_pure_old(op, old_op, start_index):
                    if isinstance(old_op, PreambleOp):
                        old_op = self.optimizer.force_op_from_preamble(old_op)
                        self.extra_call_pure[i] = old_op
                    return
        if self.known_result_call_pure:
            # needs different logic, since the result does not come from a real
            # call at all
            for i, known_result_op in enumerate(self.known_result_call_pure):
                if op.getdescr() is not known_result_op.getdescr():
                    continue
                if self._same_args(known_result_op, op, 1, start_index):
                    self.make_equal_to(op, known_result_op.getarg(0))
                    self.last_emitted_operation = REMOVED
                    return

        # replace CALL_PURE with just CALL (but keep COND_CALL_VALUE)
        if start_index == 0:
            opnum = OpHelpers.call_for_descr(op.getdescr())
            newop = self.optimizer.replace_op_with(op, opnum)
        else:
            newop = op
        return self.emit_result(CallPureOptimizationResult(self, newop))

    def optimize_CALL_PURE_I(self, op):
        return self.optimize_call_pure(op)
    optimize_CALL_PURE_R = optimize_CALL_PURE_I
    optimize_CALL_PURE_F = optimize_CALL_PURE_I
    optimize_CALL_PURE_N = optimize_CALL_PURE_I

    def optimize_COND_CALL_VALUE_I(self, op):
        return self.optimize_call_pure(op, start_index=1)
    optimize_COND_CALL_VALUE_R = optimize_COND_CALL_VALUE_I

    def _same_args(self, op1, op2, start_index1, start_index2):
        j = start_index2
        for i in range(start_index1, op1.numargs()):
            box = get_box_replacement(op1.getarg(i))
            if not get_box_replacement(op2.getarg(j)).same_box(box):
                return False
            j += 1
        return True

    def optimize_call_pure_old(self, op, old_op, start_index):
        if op.getdescr() is not old_op.getdescr():
            return False
        # this will match a call_pure and a cond_call_value with
        # the same function and arguments
        old_start_index = OpHelpers.is_cond_call_value(old_op.opnum)
        if self._same_args(old_op, op, old_start_index, start_index):
            # all identical
            # this removes a CALL_PURE that has the same (non-constant)
            # arguments as a previous CALL_PURE.
            if isinstance(old_op, PreambleOp):
                # xxx obscure, it's dealt with in the caller
                old_op = old_op.op
            self.make_equal_to(op, old_op)
            self.last_emitted_operation = REMOVED
            return True
        return False

    def optimize_GUARD_NO_EXCEPTION(self, op):
        if self.last_emitted_operation is REMOVED:
            # it was a CALL_PURE that was killed; so we also kill the
            # following GUARD_NO_EXCEPTION
            return
        return self.emit(op)

    def optimize_RECORD_KNOWN_RESULT(self, op):
        # remove the op, but keep the into about the result of the pure call
        self.known_result_call_pure.append(op)

    def flush(self):
        assert self.postponed_op is None

    def setup(self):
        self.optimizer.optpure = self

    def pure(self, opnum, op):
        recentops = self.getrecentops(opnum)
        recentops.add(op)

    def pure_from_args(self, opnum, args, op, descr=None):
        newop = ResOperation(opnum,
                             [get_box_replacement(arg) for arg in args],
                             descr=descr)
        newop.set_forwarded(op)
        self.pure(opnum, newop)

    def get_pure_result(self, op):
        recentops = self.getrecentops(op.getopnum(), create=False)
        if not recentops:
            return None
        return recentops.lookup(self.optimizer, op)

    def produce_potential_short_preamble_ops(self, sb):
        ops = self.optimizer._newoperations
        for i, op in enumerate(ops):
            if rop.is_always_pure(op.opnum):
                sb.add_pure_op(op)
            if rop.is_ovf(op.opnum) and ops[i + 1].getopnum() == rop.GUARD_NO_OVERFLOW:
                sb.add_pure_op(op)
        for i in self.call_pure_positions:
            op = ops[i]
            # don't move call_pure_with_exception in the short preamble...
            # issue #2015

            # Also, don't move cond_call_value in the short preamble.
            # The issue there is that it's usually pointless to try to
            # because the 'value' argument is typically not a loop
            # invariant, and would really need to be in order to end up
            # in the short preamble.  Maybe the code works anyway in the
            # other rare case, but better safe than sorry and don't try.
            effectinfo = op.getdescr().get_extra_info()
            if not effectinfo.check_can_raise(ignore_memoryerror=True):
                assert rop.is_call(op.opnum)
                if not OpHelpers.is_cond_call_value(op.opnum):
                    sb.add_pure_op(op)

dispatch_opt = make_dispatcher_method(OptPure, 'optimize_',
                                      default=OptPure.optimize_default)
OptPure.propagate_postprocess = make_dispatcher_method(OptPure, 'postprocess_')
OptPure.have_postprocess_op = have_dispatcher_method(OptPure, 'postprocess_')
