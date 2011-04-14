import py
from pypy.rlib.jit import JitDriver
from pypy.jit.metainterp.test import test_loop
from pypy.jit.metainterp.test.support import LLJitMixin, OOJitMixin
from pypy.jit.metainterp.optimizeopt import ALL_OPTS_NAMES

class LoopUnrollTest(test_loop.LoopTest):
    enable_opts = ALL_OPTS_NAMES
    
    automatic_promotion_result = {
        'int_add' : 3, 'int_gt' : 1, 'guard_false' : 1, 'jump' : 1, 
    }

    # ====> test_loop.py

class TestLLtype(LoopUnrollTest, LLJitMixin):
    pass

class TestOOtype(LoopUnrollTest, OOJitMixin):
    pass
