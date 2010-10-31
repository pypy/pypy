
from pypy.jit.metainterp.test import test_loop, test_send
from pypy.jit.metainterp.warmspot import ll_meta_interp
from pypy.rlib.jit import OPTIMIZER_NO_PERFECTSPEC
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin

class LoopNoPSpecTest(test_send.SendTests):
    def meta_interp(self, func, args, **kwds):
        return ll_meta_interp(func, args, optimizer=OPTIMIZER_NO_PERFECTSPEC,
                              CPUClass=self.CPUClass, 
                              type_system=self.type_system,
                              **kwds)

    def check_loops(self, *args, **kwds):
        pass

    def check_loop_count(self, count):
        pass

    def check_jumps(self, maxcount):
        pass


class TestLLtype(LoopNoPSpecTest, LLJitMixin):
    def check_tree_loop_count(self, count):
        # we get one less entry bridge
        return LLJitMixin.check_tree_loop_count(self, count - 1)

class TestOOtype(LoopNoPSpecTest, OOJitMixin):
    pass
