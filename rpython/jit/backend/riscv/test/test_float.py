#!/usr/bin/env python

from rpython.jit.backend.riscv.test.test_basic import JitRISCVMixin
from rpython.jit.metainterp.test.test_float import FloatTests


class TestFloat(JitRISCVMixin, FloatTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_float.py
    pass
