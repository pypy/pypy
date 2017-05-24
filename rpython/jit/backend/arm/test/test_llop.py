from rpython.jit.backend.arm.test.support import JitARMMixin
from rpython.jit.metainterp.test.test_llop import TestLLOp as _TestLLOp


class TestLLOp(JitARMMixin, _TestLLOp):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_llop.py
    pass

