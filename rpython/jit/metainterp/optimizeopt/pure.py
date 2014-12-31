from rpython.jit.metainterp.optimizeopt.optimizer import Optimization, REMOVED
from rpython.jit.metainterp.resoperation import rop, ResOperation, OpHelpers
from rpython.jit.metainterp.optimizeopt.util import (make_dispatcher_method,
    args_dict)

class OptPure(Optimization):
    def __init__(self):
        self.postponed_op = None
        self.pure_operations = args_dict()
        self.emitted_pure_operations = {}

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

        args = None
        remember = None
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
            args = self.optimizer.make_args_key(op.getopnum(),
                                                op.getarglist(), op.getdescr())
            oldval = self.pure_operations.get(args, None)
            if oldval is not None:
                self.optimizer.make_equal_to(op, oldval, True)
                return
            else:
                remember = op

        # otherwise, the operation remains
        self.emit_operation(op)
        if op.returns_bool_result():
            self.optimizer.bool_boxes[self.getvalue(op)] = None
        if nextop:
            self.emit_operation(nextop)
        if args is not None:
            self.pure_operations[args] = self.getvalue(op.result)
        if remember:
            self.remember_emitting_pure(remember)

    def optimize_CALL_PURE_I(self, op):
        # Step 1: check if all arguments are constant
        result = self._can_optimize_call_pure(op)
        if result is not None:
            # this removes a CALL_PURE with all constant arguments.
            self.make_constant(op, result)
            self.last_emitted_operation = REMOVED
            return

        # Step 2: check if all arguments are the same as a previous
        # CALL_PURE.
        args = self.optimizer.make_args_key(op.getopnum(), op.getarglist(),
                                            op.getdescr())
        oldval = self.pure_operations.get(args, None)
        if oldval is not None:
            assert oldop.getopnum() == op.getopnum()
            # this removes a CALL_PURE that has the same (non-constant)
            # arguments as a previous CALL_PURE.
            self.make_equal_to(op, oldval)
            self.last_emitted_operation = REMOVED
            return
        else:
            self.pure_operations[args] = self.getvalue(op.result)

        # replace CALL_PURE with just CALL
        args = op.getarglist()
        opnum = OpHelpers.call_for_descr(op.getdescr())
        newop = self.optimizer.replace_op_with(op, opnum)
        self.remember_emitting_pure(op)
        self.emit_operation(newop)
    optimize_CALL_PURE_R = optimize_CALL_PURE_I
    optimize_CALL_PURE_F = optimize_CALL_PURE_I
    optimize_CALL_PURE_N = optimize_CALL_PURE_I

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
        key = self.optimizer.make_args_key(opnum, args, None)
        if key not in self.pure_operations:
            self.pure_operations[key] = self.getvalue(result)

    def has_pure_result(self, opnum, args, descr):
        key = self.optimizer.make_args_key(opnum, args, descr)
        return self.pure_operations.get(key, None) is not None

    def get_pure_result(self, key):
        return self.pure_operations.get(key, None)

    def remember_emitting_pure(self, op):
        op = self.optimizer.get_op_replacement(op)
        self.emitted_pure_operations[op] = True

    def produce_potential_short_preamble_ops(self, sb):
        for op in self.emitted_pure_operations:
            sb.add_potential(op, op)

dispatch_opt = make_dispatcher_method(OptPure, 'optimize_',
                                      default=OptPure.optimize_default)
