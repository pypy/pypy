#!/usr/bin/env python

from rpython.jit.backend.riscv.test.test_basic import JitRISCVMixin
from rpython.jit.metainterp.test import test_string


class TestString(JitRISCVMixin, test_string.TestLLtype):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_string.py
    pass


class TestUnicode(JitRISCVMixin, test_string.TestLLtypeUnicode):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_string.py
    pass
