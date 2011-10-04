from pypy.jit.metainterp.optimizeopt.optimizer import Optimization
from pypy.jit.metainterp.optimizeopt.vstring import VAbstractStringValue
from pypy.jit.metainterp.resoperation import rop, ResOperation

class OptEarlyForce(Optimization):
    def propagate_forward(self, op):
        opnum = op.getopnum()
        if (opnum != rop.SETFIELD_GC and 
            opnum != rop.SETARRAYITEM_GC and
            opnum != rop.QUASIIMMUT_FIELD):
               
            for arg in op.getarglist():
                if arg in self.optimizer.values:
                    value = self.getvalue(arg)
                    value.force_box(self)
        self.emit_operation(op)

    def new(self):
        return OptEarlyForce()

    def setup(self):
        self.optimizer.optearlyforce = self

    
