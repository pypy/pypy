import pytest
from rpython.jit.metainterp.optimizeopt.test.test_util import (
    LLtypeMixin)
from rpython.jit.metainterp.optimizeopt.test.test_optimizebasic import (
    BaseTestBasic)
from rpython.jit.metainterp.history import ConstInt, ConstPtr
from rpython.jit.metainterp.optimize import InvalidLoop

class TestCompatible(BaseTestBasic, LLtypeMixin):

    enable_opts = "intbounds:rewrite:virtualize:string:earlyforce:pure:heap"

    def test_guard_compatible_and_guard_value(self):
        ops = """
        [p1]
        guard_value(p1, ConstPtr(myptr)) []
        guard_compatible(p1, ConstPtr(myptr)) []
        jump(ConstPtr(myptr))
        """
        expected = """
        [p1]
        guard_value(p1, ConstPtr(myptr)) []
        jump(ConstPtr(myptr))
        """
        self.optimize_loop(ops, expected)

        ops = """
        [p1]
        guard_compatible(p1, ConstPtr(myptr)) []
        guard_value(p1, ConstPtr(myptr)) []
        jump(ConstPtr(myptr))
        """
        self.optimize_loop(ops, expected)

    def test_guard_compatible_and_guard_nonnull(self):
        ops = """
        [p1]
        guard_nonnull(p1) []
        guard_compatible(p1, ConstPtr(myptr)) []
        guard_nonnull(p1) []
        jump(ConstPtr(myptr))
        """
        expected = """
        [p1]
        guard_nonnull(p1) []
        guard_compatible(p1, ConstPtr(myptr)) []
        jump(ConstPtr(myptr))
        """
        self.optimize_loop(ops, expected)

    def test_guard_compatible_and_guard_class(self):
        ops = """
        [p1]
        guard_class(p1, ConstClass(node_vtable)) []
        guard_compatible(p1, ConstPtr(myptr)) []
        guard_class(p1, ConstClass(node_vtable)) []
        jump(ConstPtr(myptr))
        """
        expected = """
        [p1]
        guard_class(p1, ConstClass(node_vtable)) []
        guard_compatible(p1, ConstPtr(myptr)) []
        jump(ConstPtr(myptr))
        """
        self.optimize_loop(ops, expected)

    def test_guard_compatible_after_guard_compatible(self):
        ops = """
        [p1]
        guard_compatible(p1, ConstPtr(myptr)) []
        guard_compatible(p1, ConstPtr(myptr)) []
        jump(ConstPtr(myptr))
        """
        expected = """
        [p1]
        guard_compatible(p1, ConstPtr(myptr)) []
        jump(ConstPtr(myptr))
        """
        self.optimize_loop(ops, expected)

    def test_guard_compatible_inconsistent(self):
        ops = """
        [p1]
        guard_compatible(p1, ConstPtr(myptr)) []
        guard_compatible(p1, ConstPtr(myptrb)) []
        jump(ConstPtr(myptr))
        """
        pytest.raises(InvalidLoop, self.optimize_loop, ops, ops)

    def test_guard_compatible_call_pure(self):
        call_pure_results = {
            (ConstInt(123), ConstPtr(self.myptr)): ConstInt(5),
            (ConstInt(124), ConstPtr(self.myptr)): ConstInt(7),
        }
        ops1 = """
        [p1]
        guard_compatible(p1, ConstPtr(myptr)) []
        i3 = call_pure_i(123, p1, descr=plaincalldescr)
        escape_n(i3)
        i5 = call_pure_i(124, p1, descr=plaincalldescr)
        escape_n(i5)
        jump(ConstPtr(myptr))
        """
        ops2 = """
        [p1]
        guard_compatible(p1, ConstPtr(myptr)) []
        i3 = call_pure_i(123, p1, descr=plaincalldescr)
        escape_n(i3)
        guard_compatible(p1, ConstPtr(myptr)) []
        i5 = call_pure_i(124, p1, descr=plaincalldescr)
        escape_n(i5)
        jump(ConstPtr(myptr))
        """
        expected = """
        [p1]
        guard_compatible(p1, ConstPtr(myptr)) []
        escape_n(5)
        escape_n(7)
        jump(ConstPtr(myptr))
        """
        for ops in [ops1, ops2]:
            self.optimize_loop(ops, expected, call_pure_results=call_pure_results)
            # whitebox-test the guard_compatible descr a bit
            descr = self.loop.operations[1].getdescr()
            assert descr._compatibility_conditions is not None
            assert descr._compatibility_conditions.known_valid.same_constant(ConstPtr(self.myptr))
            assert len(descr._compatibility_conditions.conditions) == 2

    def test_guard_compatible_call_pure_late_constant(self):
        call_pure_results = {
            (ConstInt(123), ConstPtr(self.myptr), ConstInt(5)): ConstInt(5),
            (ConstInt(124), ConstPtr(self.myptr), ConstInt(5)): ConstInt(7),
        }
        ops = """
        [p1]
        pvirtual = new_with_vtable(descr=nodesize)
        setfield_gc(pvirtual, 5, descr=valuedescr)
        i1 = getfield_gc_i(pvirtual, descr=valuedescr)
        guard_compatible(p1, ConstPtr(myptr)) []
        i3 = call_pure_i(123, p1, i1, descr=plaincalldescr)
        escape_n(i3)
        i5 = call_pure_i(124, p1, i1, descr=plaincalldescr)
        escape_n(i5)
        jump(ConstPtr(myptr))
        """
        expected = """
        [p1]
        guard_compatible(p1, ConstPtr(myptr)) []
        escape_n(5)
        escape_n(7)
        jump(ConstPtr(myptr))
        """
        self.optimize_loop(ops, expected, call_pure_results=call_pure_results)
        # whitebox-test the guard_compatible descr a bit
        descr = self.loop.operations[1].getdescr()
        assert descr._compatibility_conditions is not None
        assert descr._compatibility_conditions.known_valid.same_constant(ConstPtr(self.myptr))
        assert len(descr._compatibility_conditions.conditions) == 2

    def test_deduplicate_conditions(self):
        call_pure_results = {
            (ConstInt(123), ConstPtr(self.myptr)): ConstInt(5),
        }
        ops = """
        [p1]
        guard_compatible(p1, ConstPtr(myptr)) []
        i3 = call_pure_i(123, p1, descr=plaincalldescr)
        i4 = call_pure_i(123, p1, descr=plaincalldescr)
        i5 = call_pure_i(123, p1, descr=plaincalldescr)
        i6 = call_pure_i(123, p1, descr=plaincalldescr)
        escape_n(i3)
        escape_n(i4)
        escape_n(i5)
        escape_n(i6)
        jump(ConstPtr(myptr))
        """
        expected = """
        [p1]
        guard_compatible(p1, ConstPtr(myptr)) []
        escape_n(5)
        escape_n(5)
        escape_n(5)
        escape_n(5)
        jump(ConstPtr(myptr))
        """
        self.optimize_loop(ops, expected, call_pure_results=call_pure_results)
        descr = self.loop.operations[1].getdescr()
        assert descr._compatibility_conditions is not None
        assert descr._compatibility_conditions.known_valid.same_constant(ConstPtr(self.myptr))
        assert len(descr._compatibility_conditions.conditions) == 1

    def test_quasiimmut(self):
        ops = """
        [p1]
        guard_compatible(p1, ConstPtr(quasiptr)) []
        quasiimmut_field(p1, descr=quasiimmutdescr)
        guard_not_invalidated() []
        i0 = getfield_gc_i(p1, descr=quasifielddescr)
        i1 = call_pure_i(123, p1, i0, descr=nonwritedescr)
        quasiimmut_field(p1, descr=quasiimmutdescr)
        guard_not_invalidated() []
        i3 = getfield_gc_i(p1, descr=quasifielddescr)
        i4 = call_pure_i(123, p1, i3, descr=nonwritedescr)
        escape_n(i1)
        escape_n(i4)
        jump(p1)
        """
        expected = """
        [p1]
        guard_compatible(p1, ConstPtr(quasiptr)) []
        guard_not_invalidated() []
        i0 = getfield_gc_i(p1, descr=quasifielddescr) # will be removed by the backend
        escape_n(5)
        escape_n(5)
        jump(p1)
        """
        call_pure_results = {
            (ConstInt(123), ConstPtr(self.quasiptr), ConstInt(-4247)): ConstInt(5),
        }
        self.optimize_loop(ops, expected, call_pure_results)
        descr = self.loop.operations[1].getdescr()
        assert descr._compatibility_conditions is not None
        assert descr._compatibility_conditions.known_valid.same_constant(ConstPtr(self.quasiptr))
        assert len(descr._compatibility_conditions.conditions) == 1
