from pypy.jit.metainterp.optimizeopt.optimizer import MININT, MAXINT

class GeneralizationStrategy(object):
    def __init__(self, optimizer):
        self.optimizer = optimizer

    def apply(self):
        for v in self.optimizer.values.values():
            self._apply(v)

class KillHugeIntBounds(GeneralizationStrategy):
    def _apply(self, v):
        if not v.is_constant():
            if v.intbound.lower < MININT/2:
                v.intbound.lower = MININT
            if v.intbound.upper > MAXINT/2:
                v.intbound.upper = MAXINT
          
class KillIntBounds(GeneralizationStrategy):
    def _apply(self, v):
        if not v.is_constant():
            v.intbound.lower = MININT
            v.intbound.upper = MAXINT
        
