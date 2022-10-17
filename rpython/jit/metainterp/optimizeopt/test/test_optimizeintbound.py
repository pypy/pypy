from rpython.jit.metainterp.optimizeopt.test.test_optimizebasic import BaseTestBasic
from rpython.jit.metainterp.optimizeopt.intutils import MININT, MAXINT


class TestOptimizeIntBounds(BaseTestBasic):
    def test_bound_lt_add_ovf_before(self):
        ops = """
        [i0]
        i2 = int_add_ovf(i0, 10)
        guard_no_overflow() []
        i3 = int_lt(i2, 15)
        guard_true(i3) []
        i1 = int_lt(i0, 6)
        guard_true(i1) []
        jump(i0)
        """
        expected = """
        [i0]
        i2 = int_add_ovf(i0, 10)
        guard_no_overflow() []
        i3 = int_lt(i2, 15)
        guard_true(i3) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_int_neg_sequence(self):
        # check the trace that we get in practice for int_neg, via
        # ll_int_neg_ovf in rint.py
        ops = """
        [i0]
        i1 = int_lt(i0, 0)
        guard_true(i1) []
        i2 = int_eq(i0, %s)
        guard_false(i2) []
        i3 = int_neg(i0)
        i4 = int_ge(i3, 0)
        guard_true(i4) []
        """ % (MININT, )
        expected = """
        [i0]
        i1 = int_lt(i0, 0)
        guard_true(i1) []
        i2 = int_eq(i0, %s)
        guard_false(i2) []
        i3 = int_neg(i0)
        """ % (MININT, )
        self.optimize_loop(ops, expected)

