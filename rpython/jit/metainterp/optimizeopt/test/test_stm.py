from rpython.jit.metainterp.optimizeopt.test.test_optimizebasic import (
    BaseTestBasic,)
from rpython.jit.metainterp.optimizeopt.test.test_util import LLtypeMixin




class BaseTestSTM(BaseTestBasic):
    stm = True
    
    def test_simple(self):
        ops = """
        []
        stm_transaction_break()
        guard_not_forced() []
        jump()
        """
        expected = ops
        self.optimize_loop(ops, expected)



class TestLLtype(BaseTestSTM, LLtypeMixin):
    pass


