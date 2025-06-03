#!/usr/bin/env python

from rpython.jit.backend.riscv.test.test_basic import JitRISCVMixin
from rpython.jit.backend.test.test_rvmprof import BaseRVMProfTest


class TestRVMProfCall(JitRISCVMixin, BaseRVMProfTest):
    pass
