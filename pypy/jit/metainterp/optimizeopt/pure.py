from pypy.jit.metainterp.optimizeopt.optimizer import Optimization, REMOVED
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp.optimizeopt.util import (make_dispatcher_method,
    args_dict)

class OptPure(Optimization):
    def __init__(self):
        self.posponedop = None
        self.pure_operations = args_dict()
        self.emitted_pure_operations = {}

    def propagate_forward(self, op):
        dispatch_opt(self, op)

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
                resbox = self.optimizer.constant_fold(op)
                # note that INT_xxx_OVF is not done from here, and the
                # overflows in the INT_xxx operations are ignored
                self.optimizer.make_constant(op.result, resbox)
                return

            # did we do the exact same operation already?
            args = self.optimizer.make_args_key(op)
            oldop = self.pure_operations.get(args, None)
            if oldop is not None and oldop.getdescr() is op.getdescr():
                assert oldop.getopnum() == op.getopnum()
                self.optimizer.make_equal_to(op.result, self.getvalue(oldop.result),
                                   True)
                return
            else:
                self.pure_operations[args] = op
                self.remember_emitting_pure(op)

        # otherwise, the operation remains
        self.emit_operation(op)
        if op.returns_bool_result():
            self.optimizer.bool_boxes[self.getvalue(op.result)] = None        
        if nextop:
            self.emit_operation(nextop)

    def optimize_CALL_PURE(self, op):
        args = self.optimizer.make_args_key(op)
        oldop = self.pure_operations.get(args, None)
        if oldop is not None and oldop.getdescr() is op.getdescr():
            assert oldop.getopnum() == op.getopnum()
            # this removes a CALL_PURE that has the same (non-constant)
            # arguments as a previous CALL_PURE.
            self.make_equal_to(op.result, self.getvalue(oldop.result))
            self.last_emitted_operation = REMOVED
            return
        else:
            self.pure_operations[args] = op
            self.remember_emitting_pure(op)

        # replace CALL_PURE with just CALL
        args = op.getarglist()
        self.emit_operation(ResOperation(rop.CALL, args, op.result,
                                         op.getdescr()))

    def optimize_GUARD_NO_EXCEPTION(self, op):
        if self.last_emitted_operation is REMOVED:
            # it was a CALL_PURE that was killed; so we also kill the
            # following GUARD_NO_EXCEPTION
            return
        self.emit_operation(op)

    def flush(self):
        assert self.posponedop is None

    def new(self):
        assert self.posponedop is None
        return OptPure()

    def setup(self):
        self.optimizer.optpure = self

    def pure(self, opnum, args, result):
        op = ResOperation(opnum, args, result)
        key = self.optimizer.make_args_key(op)
        if key not in self.pure_operations:
            self.pure_operations[key] = op

    def has_pure_result(self, opnum, args, descr):
        op = ResOperation(opnum, args, None, descr)
        key = self.optimizer.make_args_key(op)
        op = self.pure_operations.get(key, None)
        if op is None:
            return False
        return op.getdescr() is descr

    def get_pure_result(self, key):
        return self.pure_operations.get(key, None)

    def remember_emitting_pure(self, op):
        self.emitted_pure_operations[op] = True

    def produce_potential_short_preamble_ops(self, sb):
        for op in self.emitted_pure_operations:
            if op.getopnum() == rop.GETARRAYITEM_GC_PURE or \
               op.getopnum() == rop.STRGETITEM or \
               op.getopnum() == rop.UNICODEGETITEM:
                if not self.getvalue(op.getarg(1)).is_constant():
                    continue
            sb.add_potential(op)

dispatch_opt = make_dispatcher_method(OptPure, 'optimize_',
                                      default=OptPure.optimize_default)
