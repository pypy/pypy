from rpython.jit.metainterp.optimizeopt.test.test_optimizebasic import BaseTestBasic
from rpython.jit.metainterp.optimizeopt.intutils import MININT, MAXINT


class TestOptimizeIntBounds(BaseTestBasic):
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

