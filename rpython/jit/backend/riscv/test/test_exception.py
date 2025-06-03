#!/usr/bin/env python

from rpython.jit.backend.riscv.test.test_basic import JitRISCVMixin
from rpython.jit.metainterp.test.test_exception import ExceptionTests


class TestExceptions(JitRISCVMixin, ExceptionTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_exception.py
    pass
