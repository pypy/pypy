import py
from pypy.jit.metainterp.test import test_loop
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin

class LoopSpecTest(test_loop.LoopTest):
    specialize = True

    # ====> test_loop.py

class TestLLtype(LoopSpecTest, LLJitMixin):
    pass

class TestOOtype(LoopSpecTest, OOJitMixin):
    pass
