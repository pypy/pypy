import py
from pypy.rlib.jit import OPTIMIZER_FULL
from pypy.jit.metainterp.test import test_loop
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin

class LoopSpecTest(test_loop.LoopTest):
    optimizer = OPTIMIZER_FULL
    automatic_promotion_result = {
        'int_add' : 3, 'int_gt' : 1, 'guard_false' : 1, 'jump' : 1, 
    }

    # ====> test_loop.py

class TestLLtype(LoopSpecTest, LLJitMixin):
    pass

class TestOOtype(LoopSpecTest, OOJitMixin):
    pass
