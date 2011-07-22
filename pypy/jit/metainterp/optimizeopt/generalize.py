from pypy.jit.metainterp.optimizeopt.optimizer import MININT, MAXINT

class GeneralizationStrategy(object):
    def __init__(self, optimizer):
        self.optimizer = optimizer

    def apply(self):
        raise NotImplementedError

class KillHugeIntBounds(GeneralizationStrategy):
    def apply(self):
        for v in self.optimizer.values.values():
            if v.is_constant():
                continue
            if v.intbound.lower < MININT/2:
                v.intbound.lower = MININT
            if v.intbound.upper > MAXINT/2:
                v.intbound.upper = MAXINT
          
