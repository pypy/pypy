import py
from pypy.jit.backend.x86.test.test_basic import Jit386Mixin
from pypy.jit.metainterp.test import test_loop_spec

class TestLoopSpec(Jit386Mixin, test_loop_spec.LoopSpecTest):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_loop.py
    pass
