#!/usr/bin/env python

from rpython.jit.backend.riscv.test.test_basic import JitRISCVMixin
from rpython.jit.metainterp.test import test_call


class TestCall(JitRISCVMixin, test_call.CallTest):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_call.py
    pass
