#!/usr/bin/env python

from rpython.jit.backend.riscv import registers as r
from rpython.jit.backend.riscv.codebuilder import InstrBuilder
from rpython.jit.backend.test.calling_convention_test import CallingConvTests
from rpython.rlib import rmmap


class TestRISCVCallingConvention(CallingConvTests):
    # ../../test/calling_convention_test.py

    def make_function_returning_stack_pointer(self):
        rmmap.enter_assembler_writing()
        try:
            mc = InstrBuilder()
            mc.MV(r.x10.value, r.sp.value)
            mc.RET()
            return mc.materialize(self.cpu, [])
        finally:
            rmmap.leave_assembler_writing()

    def get_alignment_requirements(self):
        return 16
