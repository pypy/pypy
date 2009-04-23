
from pypy.jit.metainterp.test import test_loop
from pypy.jit.metainterp.warmspot import ll_meta_interp
from pypy.jit.metainterp.simple_optimize import Optimizer
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin

class LoopDummyTest(test_loop.LoopTest):
    def meta_interp(self, func, args, **kwds):
        return ll_meta_interp(func, args, optimizer=Optimizer,
                              CPUClass=self.CPUClass, 
                              type_system=self.type_system,
                              **kwds)


class TestLLtype(LoopDummyTest, LLJitMixin):
    pass

class TestOOtype(LoopDummyTest, OOJitMixin):
    pass
