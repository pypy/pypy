
from pypy.jit.metainterp.test import test_loop
from pypy.jit.metainterp.warmspot import ll_meta_interp
from pypy.jit.metainterp.simple_optimize import optimize_loop, optimize_bridge

class Optimizer:
    optimize_loop = staticmethod(optimize_loop)
    optimize_bridge = staticmethod(optimize_bridge)

class TestLoopDummy(test_loop.TestLoop):
    def meta_interp(self, func, args, **kwds):
        return ll_meta_interp(func, args, optimizer=Optimizer, **kwds)
