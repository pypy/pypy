#!/usr/bin/env python

from rpython.jit.backend.riscv.test.test_basic import JitRISCVMixin
from rpython.jit.metainterp.test.test_del import DelTests


class TestDel(JitRISCVMixin, DelTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_del.py
    pass
