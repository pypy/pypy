#!/usr/bin/env python

from rpython.jit.backend.riscv.test.test_basic import JitRISCVMixin
from rpython.jit.metainterp.test.test_dict import DictTests


class TestDict(JitRISCVMixin, DictTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_dict.py
    pass
