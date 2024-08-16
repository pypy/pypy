#!/usr/bin/env python

from rpython.jit.backend.riscv.test.test_basic import JitRISCVMixin
from rpython.jit.backend.test.jitlog_test import LoggerTest


class TestJitlog(JitRISCVMixin, LoggerTest):
    # for the individual tests see
    # ====> ../../../test/jitlog_test.py
    pass
