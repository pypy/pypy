from rpython.jit.metainterp.optimizeopt.test.test_optimizeopt import (
    BaseTestWithUnroll,)
from rpython.jit.metainterp.optimizeopt.test.test_util import LLtypeMixin
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.rtyper.lltypesystem import lltype, rclass, rffi, llmemory


class TestSTM(BaseTestWithUnroll, LLtypeMixin):
    stm = True

    FUNC = lltype.FuncType([], lltype.Signed)
    sbtdescr = LLtypeMixin.cpu.calldescrof(
        FUNC, FUNC.ARGS, FUNC.RESULT,
        EffectInfo([], [], [], [],
                   EffectInfo.EF_CANNOT_RAISE,
                   oopspecindex=EffectInfo.OS_JIT_STM_SHOULD_BREAK_TRANSACTION,
                   can_invalidate=False)
    )
    namespace = LLtypeMixin.namespace.copy()
    namespace.update(locals())
        
    
    def test_simple(self):
        ops = """
        []
        stm_transaction_break()
        guard_not_forced() []
        jump()
        """
        expected = ops
        self.optimize_loop(ops, expected)

    def test_unrolled_loop(self):
        ops = """
        []
        i0 = call(123, descr=sbtdescr)
        stm_transaction_break()
        guard_not_forced() []
        guard_false(i0) []
        jump()
        """
        preamble = """
        []
        stm_transaction_break()
        guard_not_forced() []
        jump()
        """
        expected = """
        []
        i0 = call(123, descr=sbtdescr)
        guard_false(i0) []
        jump()
        """
        self.optimize_loop(ops, expected, expected_preamble=preamble)

    def test_unrolled_loop2(self):
        ops = """
        []
        stm_transaction_break()
        guard_not_forced() []

        i0 = call(123, descr=sbtdescr)
        stm_transaction_break()
        guard_not_forced() []
        guard_false(i0) []

        jump()
        """
        preamble = """
        []
        stm_transaction_break()
        guard_not_forced() []

        i0 = call(123, descr=sbtdescr)
        guard_false(i0) []
        
        jump()
        """
        expected = """
        []
        stm_transaction_break()
        guard_not_forced() []

        i0 = call(123, descr=sbtdescr)
        guard_false(i0) []
        jump()
        """
        self.optimize_loop(ops, expected, expected_preamble=preamble)

    def test_not_disable_opt(self):
        ops = """
        [p1]
        i0 = call(123, descr=sbtdescr)
        stm_transaction_break()
        guard_not_forced() []
        guard_false(i0) []

        i1 = getfield_gc(p1, descr=adescr)
        
        jump(p1)
        """
        preamble = """
        [p1]
        stm_transaction_break()
        guard_not_forced() []

        i1 = getfield_gc(p1, descr=adescr)

        jump(p1)
        """
        expected = """
        [p1]
        i0 = call(123, descr=sbtdescr)
        guard_false(i0) []
        
        jump(p1)
        """
        self.optimize_loop(ops, expected, expected_preamble=preamble)









        
