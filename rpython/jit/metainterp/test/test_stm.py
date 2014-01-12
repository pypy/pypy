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
        self.check_operations_history({})

    def test_not_removed(self):
        import time
        def g():
            time.sleep(0)
            return rstm.jit_stm_should_break_transaction(False)
        res = self.interp_operations(g, [], translationoptions={"stm":True})
        assert res == False
        self.check_operations_history(call=1, call_may_force=1)
        
            
    

class TestLLtype(STMTests, LLJitMixin):
    pass
