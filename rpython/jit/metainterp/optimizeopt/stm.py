from rpython.jit.metainterp.history import (Const, ConstInt, BoxInt, BoxFloat,
    BoxPtr, make_hashable_int)
from rpython.jit.metainterp.optimizeopt.optimizer import (Optimization, REMOVED,
    CONST_0, CONST_1)
from rpython.jit.metainterp.optimizeopt.util import make_dispatcher_method
from rpython.jit.metainterp.resoperation import (opboolinvers, opboolreflex, rop,
    ResOperation)
from rpython.jit.codewriter.effectinfo import EffectInfo

class OptSTM(Optimization):
    """
    For now only changes some guarded transaction breaks
    to unconditional ones.
    """
    def __init__(self):
        self.remove_next_break = False
        self.remove_next_gnf = False

    def propagate_forward(self, op):
        dispatch_opt(self, op)

    def _seen_unconditional_break(self):
        return self.optimizer.stm_info.get('seen_unconditional_break', False)
        
    def optimize_CALL(self, op):
        effectinfo = op.getdescr().get_extra_info()
        oopspecindex = effectinfo.oopspecindex
        if oopspecindex == EffectInfo.OS_JIT_STM_SHOULD_BREAK_TRANSACTION:
            if not self._seen_unconditional_break():
                self.make_constant_int(op.result, False)
                return
            else:
                self.remove_next_break = True
        self.emit_operation(op)


    def optimize_STM_TRANSACTION_BREAK(self, op):
        self.optimizer.stm_info['seen_unconditional_break'] = True
        
        if self.remove_next_break:
            self.remove_next_break = False
            self.remove_next_gnf = True
        else:
            self.emit_operation(op)

    def optimize_GUARD_NOT_FORCED(self, op):
        if self.remove_next_gnf:
            self.remove_next_gnf = False
        else:
            self.emit_operation(op)
        
        

dispatch_opt = make_dispatcher_method(OptSTM, 'optimize_',
                                      default=OptSTM.emit_operation)





