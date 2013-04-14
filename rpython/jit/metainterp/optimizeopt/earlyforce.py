from rpython.jit.metainterp.optimizeopt.optimizer import Optimization
from rpython.jit.metainterp.optimizeopt.vstring import VAbstractStringValue
from rpython.jit.metainterp.resoperation import rop, ResOperation

class OptEarlyForce(Optimization):
    def propagate_forward(self, op):
        opnum = op.getopnum()
        if (opnum != rop.SETFIELD_GC and 
            opnum != rop.SETARRAYITEM_GC and
            opnum != rop.QUASIIMMUT_FIELD and
            opnum != rop.SAME_AS and
            opnum != rop.MARK_OPAQUE_PTR):
               
            for arg in op.getarglist():
                if arg in self.optimizer.values:
                    value = self.getvalue(arg)
                    value.force_box(self)
        self.emit_operation(op)

    def new(self):
        return OptEarlyForce()

    def setup(self):
        self.optimizer.optearlyforce = self

    
