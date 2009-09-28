# xxx mostly pointless

from pypy.jit.metainterp.test import test_loop, test_send
from pypy.jit.metainterp.warmspot import ll_meta_interp
from pypy.rlib.jit import OPTIMIZER_SIMPLE
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin

class LoopDummyTest(test_send.SendTests):
    def meta_interp(self, func, args, **kwds):
        return ll_meta_interp(func, args, optimizer=OPTIMIZER_SIMPLE,
                              CPUClass=self.CPUClass, 
                              type_system=self.type_system,
                              **kwds)

    def check_loops(self, *args, **kwds):
        pass

    def check_loop_count(self, count):
        pass

    def check_jumps(self, maxcount):
        pass

class TestLLtype(LoopDummyTest, LLJitMixin):
    pass

class TestOOtype(LoopDummyTest, OOJitMixin):
    pass
