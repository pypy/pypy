from rpython.jit.metainterp.history import (Const, ConstInt, BoxInt, BoxFloat,
    BoxPtr, make_hashable_int)
from rpython.jit.metainterp.optimizeopt.optimizer import (Optimization, REMOVED,
    CONST_0, CONST_1)
from rpython.jit.metainterp.optimizeopt.util import make_dispatcher_method
from rpython.jit.metainterp.resoperation import (opboolinvers, opboolreflex, rop,
    ResOperation)


class OptSTM(Optimization):
    """
    For now only changes some guarded transaction breaks
    to unconditional ones.
    """
    def __init__(self):
        pass
    
    def new(self):
        return OptSTM()

    def propagate_forward(self, op):
        dispatch_opt(self, op)
        
    def optimize_CALL(self, op):
        self.emit_operation(op)

    def optimize_STM_TRANSACTION_BREAK(self, op):
        self.emit_operation(op)

dispatch_opt = make_dispatcher_method(OptSTM, 'optimize_',
                                      default=OptSTM.emit_operation)





