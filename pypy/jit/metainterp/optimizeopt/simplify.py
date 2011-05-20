
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.optimizeopt.optimizer import Optimization
from pypy.jit.metainterp.optimizeutil import _findall

class OptSimplify(Optimization):
    def optimize_CALL_PURE(self, op):
        args = op.getarglist()
        self.emit_operation(ResOperation(rop.CALL, args, op.result,
                                         op.getdescr()))

    def optimize_CALL_LOOPINVARIANT(self, op):
        op = op.copy_and_change(rop.CALL)
        self.emit_operation(op)

    def optimize_VIRTUAL_REF_FINISH(self, op):
        pass

    def optimize_VIRTUAL_REF(self, op):
        op = ResOperation(rop.SAME_AS, [op.getarg(0)], op.result)
        self.emit_operation(op)

    def optimize_QUASIIMMUT_FIELD(self, op):
        # xxx ideally we could also kill the following GUARD_NOT_INVALIDATED
        #     but it's a bit hard to implement robustly if heap.py is also run
        pass

    def optimize_PARTIAL_VIRTUALIZABLE(self, op):
        pass

    def propagate_forward(self, op):
        opnum = op.getopnum()
        for value, func in optimize_ops:
            if opnum == value:
                func(self, op)
                break
        else:
            self.emit_operation(op)

optimize_ops = _findall(OptSimplify, 'optimize_')
