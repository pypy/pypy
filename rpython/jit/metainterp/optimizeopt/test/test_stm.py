from rpython.jit.metainterp.optimizeopt.test.test_optimizeopt import (
    BaseTestWithUnroll,)
from rpython.jit.metainterp.optimizeopt.test.test_util import LLtypeMixin
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.rtyper.lltypesystem import lltype, rclass, rffi, llmemory


class TestSTM(BaseTestWithUnroll, LLtypeMixin):
    stm = True

    namespace = LLtypeMixin.namespace.copy()
    namespace.update(locals())


    def test_unrolled_loop(self):
        ops = """
        []
        i0 = stm_should_break_transaction()
        guard_false(i0) []
        jump()
        """
        self.optimize_loop(ops, ops, expected_preamble=ops)

    def test_really_wanted_tb(self):
        ops = """
        []
        stm_transaction_break(0)
        guard_not_forced() []

        stm_transaction_break(1)
        guard_not_forced() []

        jump()
        """
        preamble = """
        []
        stm_transaction_break(0)
        guard_not_forced() []

        stm_transaction_break(1)
        guard_not_forced() []

        jump()
        """
        expected = """
        []
        stm_transaction_break(1)
        guard_not_forced() []

        jump()
        """
        self.optimize_loop(ops, expected, expected_preamble=preamble)


    def test_unrolled_loop2(self):
        ops = """
        []
        stm_transaction_break(0)
        guard_not_forced() []

        i0 = stm_should_break_transaction()
        guard_false(i0) []

        jump()
        """
        preamble = """
        []
        stm_transaction_break(0)
        guard_not_forced() []

        i0 = stm_should_break_transaction()
        guard_false(i0) []
        
        jump()
        """
        expected = """
        []
        i0 = stm_should_break_transaction()
        guard_false(i0) []
        jump()
        """
        self.optimize_loop(ops, expected, expected_preamble=preamble)

    def test_not_disable_opt(self):
        ops = """
        [p1]
        i1 = getfield_gc(p1, descr=adescr)

        i0 = stm_should_break_transaction()
        guard_false(i0) []
        jump(p1)
        """
        preamble = """
        [p1]
        i1 = getfield_gc(p1, descr=adescr)
        
        i0 = stm_should_break_transaction()
        guard_false(i0) []
        jump(p1)
        """
        expected = """
        [p1]
        i0 = stm_should_break_transaction()
        guard_false(i0) []
        
        jump(p1)
        """
        self.optimize_loop(ops, expected, expected_preamble=preamble)

    def test_dont_remove_first_tb(self):
        ops = """
        []
        stm_transaction_break(0)
        guard_not_forced() []
        stm_transaction_break(0)
        guard_not_forced() []
        stm_transaction_break(0)
        guard_not_forced() []
        i0 = stm_should_break_transaction()
        guard_false(i0) []
        jump()
        """
        preamble = """
        []
        stm_transaction_break(0)
        guard_not_forced() []

        i0 = stm_should_break_transaction()
        guard_false(i0) []
        jump()
        """
        expected = """
        []
        i0 = stm_should_break_transaction()
        guard_false(i0) []
        jump()
        """
        self.optimize_loop(ops, expected, expected_preamble=preamble)

    def test_add_tb_after_guard_not_forced(self):
        ops = """
        []
        stm_transaction_break(0)
        guard_not_forced() []
        
        escape() # e.g. like a call_release_gil
        guard_not_forced() []
        
        stm_transaction_break(0)
        guard_not_forced() []
        stm_transaction_break(0)
        guard_not_forced() []
        i0 = stm_should_break_transaction()
        guard_false(i0) []
        jump()
        """
        preamble = """
        []
        stm_transaction_break(0)
        guard_not_forced() []

        escape()
        guard_not_forced() []

        stm_transaction_break(0)
        guard_not_forced() []
        
        i0 = stm_should_break_transaction()
        guard_false(i0) []
        jump()
        """
        expected = """
        []
        escape()
        guard_not_forced() []

        stm_transaction_break(0)
        guard_not_forced() []

        i0 = stm_should_break_transaction()
        guard_false(i0) []
        jump()
        """
        self.optimize_loop(ops, expected, expected_preamble=preamble)

    def test_remove_force_token(self):
        ops = """
        [p0]
        p1 = force_token()
        setfield_gc(p0, p1, descr=adescr)
        stm_transaction_break(0)
        guard_not_forced() []

        p2 = force_token()
        setfield_gc(p0, p2, descr=adescr)
        stm_transaction_break(0)
        guard_not_forced() []

        p3 = force_token()
        setfield_gc(p0, p3, descr=adescr)
        stm_transaction_break(0)
        guard_not_forced() []

        escape()

        p4 = force_token()
        setfield_gc(p0, p4, descr=adescr)
        stm_transaction_break(0)
        guard_not_forced() []

        p6 = force_token() # not removed!
                
        i0 = stm_should_break_transaction()
        guard_false(i0) []
        jump(p0)
        """
        preamble = """
        [p0]
        p1 = force_token()
        setfield_gc(p0, p1, descr=adescr)
        stm_transaction_break(0)
        guard_not_forced() []

        escape()

        p6 = force_token() # not removed!
        
        i0 = stm_should_break_transaction()
        guard_false(i0) []
        jump(p0)
        """
        expected = """
        [p0]
        escape()

        p6 = force_token() # not removed!
        
        i0 = stm_should_break_transaction()
        guard_false(i0) []
        jump(p0)
        """
        self.optimize_loop(ops, expected, expected_preamble=preamble)

    def test_not_remove_setfield(self):
        ops = """
        [p0, p1]
        setfield_gc(p0, p1, descr=adescr)
        stm_transaction_break(0)
        
        p2 = force_token()
        p3 = force_token()
        jump(p0, p1)
        """
        preamble = """
        [p0, p1]
        setfield_gc(p0, p1, descr=adescr)
        stm_transaction_break(0)

        p2 = force_token()
        p3 = force_token()
        jump(p0, p1)
        """
        expected = """
        [p0, p1]
        p2 = force_token()
        p3 = force_token()
        
        setfield_gc(p0, p1, descr=adescr) # moved here by other stuff...
        jump(p0, p1)        
        """
        self.optimize_loop(ops, expected, expected_preamble=preamble)

    def test_stm_location_1(self):
        # This tests setfield_gc on a non-virtual.  On a virtual, it doesn't
        # really matter, because STM conflicts are impossible anyway
        ops = """
        [i1, p1]
        setfield_gc(p1, i1, descr=adescr) {81}
        call(i1, descr=nonwritedescr) {90}
        jump(i1, p1)
        """
        expected = """
        [i1, p1]
        call(i1, descr=nonwritedescr) {90}
        setfield_gc(p1, i1, descr=adescr) {81}
        jump(i1, p1)
        """
        self.optimize_loop(ops, expected)
