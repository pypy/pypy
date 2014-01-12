import py, sys
from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.rlib.jit import JitDriver, dont_look_inside
from rpython.rlib.rarithmetic import ovfcheck, LONG_BIT, intmask
from rpython.jit.codewriter.policy import StopAtXPolicy
from rpython.rlib import rstm




class STMTests:
    def test_simple(self):
        def g():
            return rstm.jit_stm_should_break_transaction(False)
        res = self.interp_operations(g, [])
        assert res == False

class TestLLtype(STMTests, LLJitMixin):
    pass
