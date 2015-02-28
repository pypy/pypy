from rpython.jit.metainterp.optimizeopt.optimizer import Optimization, REMOVED
from rpython.jit.metainterp.resoperation import rop, ResOperation
from rpython.jit.metainterp.optimizeopt.util import make_dispatcher_method


class RecentPureOps(object):
    REMEMBER_LIMIT = 16

    def __init__(self):
        self.lst = [None] * self.REMEMBER_LIMIT
        self.next_index = 0

    def add(self, op):
        next_index = self.next_index
        self.next_index = (next_index + 1) % self.REMEMBER_LIMIT
        self.lst[next_index] = op

    def lookup1(self, box0, descr):
        for i in range(self.REMEMBER_LIMIT):
            op = self.lst[i]
            if op is None:
                break
            if op.getarg(0).same_box(box0) and op.getdescr() is descr:
                return op
        return None

    def lookup2(self, box0, box1, descr):
        for i in range(self.REMEMBER_LIMIT):
            op = self.lst[i]
            if op is None:
                break
            if (op.getarg(0).same_box(box0) and op.getarg(1).same_box(box1)
                and op.getdescr() is descr):
                return op
        return None

    def lookup(self, optimizer, op):
        numargs = op.numargs()
        if numargs == 1:
            return self.lookup1(optimizer.get_box_replacement(op.getarg(0)),
                                op.getdescr())
        elif numargs == 2:
            return self.lookup2(optimizer.get_box_replacement(op.getarg(0)),
                                optimizer.get_box_replacement(op.getarg(1)),
                                op.getdescr())
        else:
            assert False


class OptPure(Optimization):
    def __init__(self):
        self.postponed_op = None
        self._pure_operations = [None] * (rop._ALWAYS_PURE_LAST -
                                          rop._ALWAYS_PURE_FIRST)
        self.call_pure_positions = []

    def propagate_forward(self, op):
        dispatch_opt(self, op)

    def optimize_default(self, op):
        canfold = op.is_always_pure()
        if op.is_ovf():
            self.postponed_op = op
            return
        if self.postponed_op:
            nextop = op
            op = self.postponed_op
            self.postponed_op = None
            canfold = nextop.getopnum() == rop.GUARD_NO_OVERFLOW
        else:
            nextop = None

        if canfold:
            for i in range(op.numargs()):
                if self.get_constant_box(op.getarg(i)) is None:
                    break
            else:
                # all constant arguments: constant-fold away
                resbox = self.optimizer.constant_fold(op)
                # note that INT_xxx_OVF is not done from here, and the
                # overflows in the INT_xxx operations are ignored
                self.optimizer.make_constant(op.result, resbox)
                return

            # did we do the exact same operation already?
            recentops = self.getrecentops(op.getopnum())
            oldop = recentops.lookup(self.optimizer, op)
            if oldop is not None:
                self.optimizer.make_equal_to(op.result, oldop.result, True)
                return

        # otherwise, the operation remains
        self.emit_operation(op)
        if op.returns_bool_result():
            self.optimizer.bool_boxes[self.getvalue(op.result)] = None
        if canfold:
            realop = self.optimizer.getlastop()
            if realop is not None:
                recentops = self.getrecentops(realop.getopnum())
                recentops.add(realop)
        if nextop:
            self.emit_operation(nextop)

    def getrecentops(self, opnum):
        opnum = opnum - rop._ALWAYS_PURE_FIRST
        assert 0 <= opnum < len(self._pure_operations)
        recentops = self._pure_operations[opnum]
        if recentops is None:
            self._pure_operations[opnum] = recentops = RecentPureOps()
        return recentops

    def optimize_CALL_PURE(self, op):
        # Step 1: check if all arguments are constant
        result = self._can_optimize_call_pure(op)
        if result is not None:
            # this removes a CALL_PURE with all constant arguments.
            self.make_constant(op.result, result)
            self.last_emitted_operation = REMOVED
            return

        # Step 2: check if all arguments are the same as a previous
        # CALL_PURE.
        args = self.optimizer.make_args_key(op)
        oldvalue = self.pure_operations.get(args, None)
        if oldvalue is not None:
            # this removes a CALL_PURE that has the same (non-constant)
            # arguments as a previous CALL_PURE.
            self.make_equal_to(op.result, oldvalue)
            self.last_emitted_operation = REMOVED
            return
        else:
            self.pure_operations[args] = self.getvalue(op.result)

        # replace CALL_PURE with just CALL
        args = op.getarglist()
        self.emit_operation(ResOperation(rop.CALL, args, op.result,
                                         op.getdescr()))
        self.call_pure_positions.append(len(self.optimizer._newoperations) - 1)

    def optimize_GUARD_NO_EXCEPTION(self, op):
        if self.last_emitted_operation is REMOVED:
            # it was a CALL_PURE that was killed; so we also kill the
            # following GUARD_NO_EXCEPTION
            return
        self.emit_operation(op)

    def flush(self):
        assert self.postponed_op is None

    def setup(self):
        self.optimizer.optpure = self

    def pure(self, opnum, args, result):
        op = ResOperation(opnum, args, result)
        recentops = self.getrecentops(opnum)
        recentops.add(op)

    def has_pure_result(self, opnum, args, descr):
        return False
        op = ResOperation(opnum, args, None, descr)
        key = self.optimizer.make_args_key(op)
        return self.pure_operations.get(key, None) is not None

    def get_pure_result(self, op):
        recentops = self.getrecentops(op.getopnum())
        return recentops.lookup(self.optimizer, op)

    def produce_potential_short_preamble_ops(self, sb):
        ops = sb.optimizer._newoperations
        for i, op in enumerate(ops):
            if op.is_always_pure():
                sb.add_potential(op)
            if op.is_ovf() and ops[i + 1].getopnum() == rop.GUARD_NO_OVERFLOW:
                sb.add_potential(op)
        for i in self.call_pure_positions:
            op = ops[i]
            assert op.getopnum() == rop.CALL
            op = op.copy_and_change(rop.CALL_PURE)
            sb.add_potential(op)

dispatch_opt = make_dispatcher_method(OptPure, 'optimize_',
                                      default=OptPure.optimize_default)
