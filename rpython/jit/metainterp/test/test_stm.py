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
        res = self.interp_operations(g, [], translationoptions={"stm":True})
        assert res == False
        self.check_operations_history(stm_transaction_break=1,
                                      stm_should_break_transaction=0)

    def test_not_removed(self):
        import time
        def g():
            time.sleep(0)
            return rstm.jit_stm_should_break_transaction(False)
        res = self.interp_operations(g, [], translationoptions={"stm":True})
        assert res == False
        self.check_operations_history(stm_transaction_break=1,
                                      call_may_force=1,
                                      stm_should_break_transaction=0)

    def test_not_removed2(self):
        def g():
            return rstm.jit_stm_should_break_transaction(True)
        res = self.interp_operations(g, [], translationoptions={"stm":True})
        assert res == False
        self.check_operations_history(stm_transaction_break=0,
                                      stm_should_break_transaction=1)

    def test_transaction_break(self):
        def g():
            rstm.jit_stm_transaction_break_point()
            return 42
        self.interp_operations(g, [], translationoptions={"stm":True})
        self.check_operations_history({'stm_transaction_break':1,
                                       'guard_not_forced':1})

    def test_heapcache(self):
        import time
        def g():
            rstm.jit_stm_should_break_transaction(True) # keep (start of loop)
            rstm.jit_stm_should_break_transaction(False)
            time.sleep(0)
            rstm.jit_stm_should_break_transaction(False) # keep (after guard_not_forced)
            rstm.jit_stm_should_break_transaction(True) # keep (True)
            rstm.jit_stm_should_break_transaction(True) # keep (True)
            rstm.jit_stm_should_break_transaction(False)
            return 42
        res = self.interp_operations(g, [], translationoptions={"stm":True})
        assert res == 42
        self.check_operations_history({
            'stm_transaction_break':1,
            'stm_should_break_transaction':3,
            'guard_not_forced':2,
            'guard_no_exception':1,
            'call_may_force':1})




class TestLLtype(STMTests, LLJitMixin):
    pass
