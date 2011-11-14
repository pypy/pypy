import py
from pypy.jit.backend.x86.test.test_basic import Jit386Mixin
from pypy.jit.metainterp.test import test_loop_unroll
from pypy.jit.backend.arm.test.support import skip_unless_arm
skip_unless_arm()

class TestLoopSpec(Jit386Mixin, test_loop_unroll.LoopUnrollTest):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_loop.py
    pass
