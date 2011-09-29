from pypy.jit.metainterp.optimizeopt.optimizer import Optimization
from pypy.jit.metainterp.optimizeopt.vstring import VAbstractStringValue

class OptEarlyForce(Optimization):
    def propagate_forward(self, op):
        for arg in op.getarglist():
            if arg in self.optimizer.values:
                value = self.getvalue(arg)
                if isinstance(value, VAbstractStringValue):
                    value.force_box(self)
        self.emit_operation(op)

    def new(self):
        return OptEarlyForce()

    def setup(self):
        self.optimizer.optearlyforce = self

    
