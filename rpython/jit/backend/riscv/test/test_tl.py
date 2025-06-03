#!/usr/bin/env python

from rpython.jit.backend.riscv.test.test_basic import JitRISCVMixin
from rpython.jit.metainterp.test.test_tl import ToyLanguageTests


class TestTL(JitRISCVMixin, ToyLanguageTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_tl.py
    pass
