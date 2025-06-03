#!/usr/bin/env python

import py
from rpython.jit.backend.riscv.test.test_basic import JitRISCVMixin
from rpython.jit.metainterp.test.test_tlc import TLCTests
from rpython.jit.tl import tlc


class TestTL(JitRISCVMixin, TLCTests):
    # for the individual tests see
    # ====> ../../test/test_tlc.py

    def test_accumulator(self):
        path = py.path.local(tlc.__file__).dirpath('accumulator.tlc.src')
        code = path.read()
        res = self.exec_code(code, 20)
        assert res == sum(range(20))
        res = self.exec_code(code, -10)
        assert res == 10

    def test_fib(self):
        py.test.skip("AnnotatorError")
        path = py.path.local(tlc.__file__).dirpath('fibo.tlc.src')
        code = path.read()
        res = self.exec_code(code, 7)
        assert res == 13
        res = self.exec_code(code, 20)
        assert res == 6765
