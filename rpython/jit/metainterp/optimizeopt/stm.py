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
        self.remove_next_gnf = False # guard_not_forced

    def propagate_forward(self, op):
        dispatch_opt(self, op)

    def _break_wanted(self):
        return self.optimizer.stm_info.get('break_wanted', True)
    
    def _set_break_wanted(self, val):
        self.optimizer.stm_info['break_wanted'] = val
        
    def optimize_CALL(self, op):
        effectinfo = op.getdescr().get_extra_info()
        oopspecindex = effectinfo.oopspecindex
        if oopspecindex == EffectInfo.OS_JIT_STM_SHOULD_BREAK_TRANSACTION:
            self._set_break_wanted(False)
        self.emit_operation(op)


    def optimize_STM_TRANSACTION_BREAK(self, op):
        assert not self.remove_next_gnf
        
        if self._break_wanted():
            self._set_break_wanted(False)
            self.emit_operation(op)
        else:
            self.remove_next_gnf = True

    def optimize_GUARD_NOT_FORCED(self, op):
        if self.remove_next_gnf:
            self.remove_next_gnf = False
        else:
            self.emit_operation(op)
        
        

dispatch_opt = make_dispatcher_method(OptSTM, 'optimize_',
                                      default=OptSTM.emit_operation)





