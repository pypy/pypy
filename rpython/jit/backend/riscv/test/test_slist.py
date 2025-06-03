#!/usr/bin/env python

import py
from rpython.jit.backend.riscv.test.test_basic import JitRISCVMixin
from rpython.jit.metainterp.test import test_slist


class TestSList(JitRISCVMixin, test_slist.ListTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_slist.py

    def test_list_of_voids(self):
        py.test.skip("list of voids unsupported by ll2ctypes")
