from rpython.jit.metainterp.optimizeopt.optimizer import (Optimization, )
from rpython.jit.metainterp.optimizeopt.util import make_dispatcher_method
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.metainterp.resoperation import rop

class OptSTM(Optimization):
    """
    For now only changes some guarded transaction breaks
    to unconditional ones.
    """
    def __init__(self):
        self.remove_next_gnf = False # guard_not_forced
        self.keep_but_ignore_gnf = False
        self.cached_ops = []

    def propagate_forward(self, op):
        dispatch_opt(self, op)

    def flush_cached(self):
        while self.cached_ops:
            self.emit_operation(self.cached_ops.pop(0))

    def flush(self):
        # just in case. it shouldn't be necessary
        self.flush_cached()
        
    def default_emit(self, op):
        self.flush_cached()
        self.emit_operation(op)

    def _break_wanted(self):
        is_loop = self.optimizer.loop.is_really_loop
        return self.optimizer.stm_info.get('break_wanted', is_loop)
    
    def _set_break_wanted(self, val):
        self.optimizer.stm_info['break_wanted'] = val

    def optimize_FORCE_TOKEN(self, op):
        # if we have cached stuff, flush it. Not our case
        self.flush_cached()
        self.cached_ops.append(op)

    def optimize_SETFIELD_GC(self, op):
        if not self.cached_ops:
            # setfield not for force_token
            self.emit_operation(op)
        else:
            assert len(self.cached_ops) == 1
            assert self.cached_ops[0].getopnum() == rop.FORCE_TOKEN
            self.cached_ops.append(op)
        
    def optimize_CALL(self, op):
        self.flush_cached()
        effectinfo = op.getdescr().get_extra_info()
        oopspecindex = effectinfo.oopspecindex
        if oopspecindex == EffectInfo.OS_JIT_STM_SHOULD_BREAK_TRANSACTION:
            self._set_break_wanted(False)
        self.emit_operation(op)

    def optimize_STM_TRANSACTION_BREAK(self, op):
        assert not self.remove_next_gnf
        really_wanted = op.getarg(0).getint()
        if really_wanted or self._break_wanted():
            self.flush_cached()
            self._set_break_wanted(False)
            self.emit_operation(op)
            self.keep_but_ignore_gnf = True
        else:
            self.cached_ops = []
            self.remove_next_gnf = True

    def optimize_GUARD_NOT_FORCED(self, op):
        self.flush_cached()
        if self.remove_next_gnf:
            self.remove_next_gnf = False
        else:
            if not self.keep_but_ignore_gnf:
                self._set_break_wanted(True)
            self.keep_but_ignore_gnf = False
            self.emit_operation(op)
        
        

dispatch_opt = make_dispatcher_method(OptSTM, 'optimize_',
                                      default=OptSTM.default_emit)





