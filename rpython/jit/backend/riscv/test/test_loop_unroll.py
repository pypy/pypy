#!/usr/bin/env python

from rpython.jit.backend.riscv.test.test_basic import JitRISCVMixin
from rpython.jit.metainterp.test import test_loop_unroll


class TestLoopSpec(JitRISCVMixin, test_loop_unroll.LoopUnrollTest):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_loop.py
    pass
