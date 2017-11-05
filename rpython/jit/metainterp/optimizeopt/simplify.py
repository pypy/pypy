from rpython.jit.metainterp.optimizeopt.optimizer import Optimization
from rpython.jit.metainterp.optimizeopt.util import make_dispatcher_method
from rpython.jit.metainterp.resoperation import ResOperation, rop, OpHelpers
from rpython.jit.metainterp.history import TargetToken, JitCellToken

class OptSimplify(Optimization):
    def __init__(self, unroll):
        self.last_label_descr = None
        self.unroll = unroll

    def emit(self, op):
        if op.is_guard():
            if self.optimizer.pendingfields is None:
                self.optimizer.pendingfields = []
        return Optimization.emit(self, op)

    def optimize_CALL_PURE_I(self, op):
        opnum = OpHelpers.call_for_descr(op.getdescr())
        newop = self.optimizer.replace_op_with(op, opnum)
        return self.emit(newop)
    optimize_CALL_PURE_R = optimize_CALL_PURE_I
    optimize_CALL_PURE_F = optimize_CALL_PURE_I
    optimize_CALL_PURE_N = optimize_CALL_PURE_I

    def optimize_CALL_LOOPINVARIANT_I(self, op):
        opnum = OpHelpers.call_for_descr(op.getdescr())
        op = op.copy_and_change(opnum)
        return self.emit(op)
    optimize_CALL_LOOPINVARIANT_R = optimize_CALL_LOOPINVARIANT_I
    optimize_CALL_LOOPINVARIANT_F = optimize_CALL_LOOPINVARIANT_I
    optimize_CALL_LOOPINVARIANT_N = optimize_CALL_LOOPINVARIANT_I

    def optimize_VIRTUAL_REF_FINISH(self, op):
        pass

    def optimize_VIRTUAL_REF(self, op):
        newop = self.replace_op_with(op, rop.SAME_AS_R, [op.getarg(0)])
        return self.emit(newop)

    def optimize_QUASIIMMUT_FIELD(self, op):
        # xxx ideally we could also kill the following GUARD_NOT_INVALIDATED
        #     but it's a bit hard to implement robustly if heap.py is also run
        pass

    def optimize_ASSERT_NOT_NONE(self, op):
        pass

    def optimize_RECORD_EXACT_CLASS(self, op):
        pass

    # def optimize_LABEL(self, op):
    #     if not self.unroll:
    #         descr = op.getdescr()
    #         if isinstance(descr, JitCellToken):
    #             return self.optimize_JUMP(op.copy_and_change(rop.JUMP))
    #         self.last_label_descr = op.getdescr()
    #     return self.emit(op)

    # def optimize_JUMP(self, op):
    #     if not self.unroll:
    #         op = op.copy_and_change(op.getopnum())
    #         descr = op.getdescr()
    #         assert isinstance(descr, JitCellToken)
    #         if not descr.target_tokens:
    #             assert self.last_label_descr is not None
    #             target_token = self.last_label_descr
    #             assert isinstance(target_token, TargetToken)
    #             assert target_token.targeting_jitcell_token is descr
    #             op.setdescr(self.last_label_descr)
    #         else:
    #             assert len(descr.target_tokens) == 1
    #             op.setdescr(descr.target_tokens[0])
    #     return self.emit(op)

    def optimize_GUARD_FUTURE_CONDITION(self, op):
        self.optimizer.notice_guard_future_condition(op)

dispatch_opt = make_dispatcher_method(OptSimplify, 'optimize_',
                                      default=OptSimplify.emit)
OptSimplify.propagate_forward = dispatch_opt
