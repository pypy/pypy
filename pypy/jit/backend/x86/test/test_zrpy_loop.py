
from pypy.jit.metainterp.test.test_loop import LoopTest
from pypy.jit.backend.x86.test.test_zrpy_slist import Jit386Mixin

class TestLoop(Jit386Mixin, LoopTest):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_loop.py
    pass
