from pypy.jit.metainterp.optimizeopt.optimizer import Optimization
from pypy.jit.metainterp.optimizeopt.util import make_dispatcher_method
from pypy.jit.metainterp.resoperation import ResOperation, rop


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


dispatch_opt = make_dispatcher_method(OptSimplify, 'optimize_',
        default=OptSimplify.emit_operation)
OptSimplify.propagate_forward = dispatch_opt
