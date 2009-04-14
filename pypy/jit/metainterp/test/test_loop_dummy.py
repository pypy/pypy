
from pypy.jit.metainterp.test import test_loop
from pypy.jit.metainterp.warmspot import ll_meta_interp
from pypy.jit.metainterp.simple_optimize import Optimizer

class TestLoopDummy(test_loop.TestLoop):
    def meta_interp(self, func, args, **kwds):
        return ll_meta_interp(func, args, optimizer=Optimizer,
                              CPUClass=self.CPUClass, **kwds)
