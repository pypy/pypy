import py
from pypy.rlib.jit import JitDriver
from pypy.jit.metainterp.test import test_loop
from pypy.jit.metainterp.test.support import LLJitMixin, OOJitMixin
from pypy.jit.metainterp.optimizeopt import ALL_OPTS_NAMES

class LoopUnrollTest(test_loop.LoopTest):
    enable_opts = ALL_OPTS_NAMES
    
    automatic_promotion_result = {
        'int_gt': 2, 'guard_false': 2, 'jump': 2, 'int_add': 6,
        'guard_value': 1        
    }

    # ====> test_loop.py

class TestLLtype(LoopUnrollTest, LLJitMixin):
    pass

class TestOOtype(LoopUnrollTest, OOJitMixin):
    pass
