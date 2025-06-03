#!/usr/bin/env python

from rpython.jit.backend.riscv.test.test_basic import JitRISCVMixin
from rpython.jit.metainterp.test.test_list import ListTests


class TestList(JitRISCVMixin, ListTests):
    # for individual tests see
    # ====> ../../../metainterp/test/test_list.py
    pass
