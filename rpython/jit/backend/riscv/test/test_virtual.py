#!/usr/bin/env python

from rpython.jit.backend.riscv.test.test_basic import JitRISCVMixin
from rpython.jit.metainterp.test.test_virtual import (
    VirtualTests, VirtualMiscTests)


class MyClass:
    pass


class TestsVirtual(JitRISCVMixin, VirtualTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_virtual.py
    _new_op = 'new_with_vtable'
    _field_prefix = 'inst_'

    @staticmethod
    def _new():
        return MyClass()


class TestsVirtualMisc(JitRISCVMixin, VirtualMiscTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_virtual.py
    pass
