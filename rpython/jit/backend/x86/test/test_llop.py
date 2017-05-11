from rpython.jit.backend.x86.test.test_basic import Jit386Mixin
from rpython.jit.metainterp.test.test_llop import TestLLOp as _TestLLOp


class TestLLOp(Jit386Mixin, _TestLLOp):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_llop.py
    pass

