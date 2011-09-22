from pypy.jit.metainterp.optimizeopt.optimizer import Optimization
from pypy.jit.metainterp.resoperation import rop, ResOperation

class OptPure(Optimization):
    def __init__(self):
        self.posponedop = None

    def propagate_forward(self, op):        
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
            oldop = self.optimizer.pure_operations.get(args, None)
            if oldop is not None and oldop.getdescr() is op.getdescr():
                assert oldop.getopnum() == op.getopnum()
                self.optimizer.make_equal_to(op.result, self.getvalue(oldop.result),
                                   True)
                return
            else:
                self.optimizer.pure_operations[args] = op
                self.optimizer.remember_emitting_pure(op)

        # otherwise, the operation remains
        self.emit_operation(op)
        if op.returns_bool_result():
            self.optimizer.bool_boxes[self.getvalue(op.result)] = None        
        if nextop:
            self.emit_operation(nextop)

    def flush(self):
        assert self.posponedop is None

    def new(self):
        assert self.posponedop is None
        return OptPure()
