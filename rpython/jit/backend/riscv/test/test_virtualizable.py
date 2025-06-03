#!/usr/bin/env python

import py
from rpython.jit.backend.riscv.test.test_basic import JitRISCVMixin
from rpython.jit.metainterp.test.test_virtualizable import ImplicitVirtualizableTests


class TestVirtualizable(JitRISCVMixin, ImplicitVirtualizableTests):
    def test_blackhole_should_not_reenter(self):
        py.test.skip("Assertion error & llinterp mess")
