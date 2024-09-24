#!/usr/bin/env python

from rpython.jit.backend.riscv.test.test_basic import JitRISCVMixin
from rpython.jit.metainterp.test.test_virtualref import VRefTests


class TestVRef(JitRISCVMixin, VRefTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_virtualref.py
    pass
