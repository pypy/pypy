import pytest
from rpython.jit.metainterp.optimizeopt.test.test_optimizebasic import BaseTestBasic
from rpython.jit.metainterp.optimizeopt.intutils import MININT, MAXINT
from rpython.jit.metainterp.optimizeopt.intdiv import magic_numbers
from rpython.rlib.rarithmetic import intmask, LONG_BIT


class TestOptimizeIntBounds(BaseTestBasic):
    def test_very_simple(self):
        ops = """
        [i]
        i0 = int_sub(i, 1)
        guard_value(i0, 0) [i0]
        jump(i0)
        """
        expected = """
        [i]
        i0 = int_sub(i, 1)
        guard_value(i0, 0) [i0]
        jump(0)
        """
        self.optimize_loop(ops, expected)

    def test_simple(self):
        ops = """
        [i]
        i0 = int_sub(i, 1)
        guard_value(i0, 0) [i0]
        jump(i)
        """
        expected = """
        [i]
        i0 = int_sub(i, 1)
        guard_value(i0, 0) [i0]
        jump(1)
        """
        self.optimize_loop(ops, expected)

    def test_constant_propagate(self):
        ops = """
        []
        i0 = int_add(2, 3)
        i1 = int_is_true(i0)
        guard_true(i1) []
        i2 = int_is_zero(i1)
        guard_false(i2) []
        guard_value(i0, 5) []
        jump()
        """
        expected = """
        []
        jump()
        """
        self.optimize_loop(ops, expected)

    def test_constant_propagate_ovf(self):
        ops = """
        []
        i0 = int_add_ovf(2, 3)
        guard_no_overflow() []
        i1 = int_is_true(i0)
        guard_true(i1) []
        i2 = int_is_zero(i1)
        guard_false(i2) []
        guard_value(i0, 5) []
        jump()
        """
        expected = """
        []
        jump()
        """
        self.optimize_loop(ops, expected)

    def test_const_guard_value(self):
        ops = """
        []
        i = int_add(5, 3)
        guard_value(i, 8) []
        jump()
        """
        expected = """
        []
        jump()
        """
        self.optimize_loop(ops, expected)

    def test_int_is_true_1(self):
        ops = """
        [i0]
        i1 = int_is_true(i0)
        guard_true(i1) []
        i2 = int_is_true(i0)
        guard_true(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_is_true(i0)
        guard_true(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_int_is_true_is_zero(self):
        ops = """
        [i0]
        i1 = int_is_true(i0)
        guard_true(i1) []
        i2 = int_is_zero(i0)
        guard_false(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_is_true(i0)
        guard_true(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

        ops = """
        [i0]
        i2 = int_is_zero(i0)
        guard_false(i2) []
        i1 = int_is_true(i0)
        guard_true(i1) []
        jump(i0)
        """
        expected = """
        [i0]
        i2 = int_is_zero(i0)
        guard_false(i2) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_int_is_zero_int_is_true(self):
        ops = """
        [i0]
        i1 = int_is_zero(i0)
        guard_true(i1) []
        i2 = int_is_true(i0)
        guard_false(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_is_zero(i0)
        guard_true(i1) []
        jump(0)
        """
        self.optimize_loop(ops, expected)

    def test_remove_duplicate_pure_op_ovf(self):
        ops = """
        [i1]
        i3 = int_add_ovf(i1, 1)
        guard_no_overflow() []
        i3b = int_is_true(i3)
        guard_true(i3b) []
        i4 = int_add_ovf(i1, 1)
        guard_no_overflow() []
        i4b = int_is_true(i4)
        guard_true(i4b) []
        jump(i3, i4)
        """
        expected = """
        [i1]
        i3 = int_add_ovf(i1, 1)
        guard_no_overflow() []
        i3b = int_is_true(i3)
        guard_true(i3b) []
        jump(i3, i3)
        """
        self.optimize_loop(ops, expected)

    def test_int_and_or_with_zero(self):
        ops = """
        [i0, i1]
        i2 = int_and(i0, 0)
        i3 = int_and(0, i2)
        i4 = int_or(i2, i1)
        i5 = int_or(i0, i3)
        jump(i4, i5)
        """
        expected = """
        [i0, i1]
        jump(i1, i0)
        """
        self.optimize_loop(ops, expected)

    def test_fold_partially_constant_ops(self):
        ops = """
        [i0]
        i1 = int_sub(i0, 0)
        jump(i1)
        """
        expected = """
        [i0]
        jump(i0)
        """
        self.optimize_loop(ops, expected)

        ops = """
        [i0]
        i1 = int_add(i0, 0)
        jump(i1)
        """
        expected = """
        [i0]
        jump(i0)
        """
        self.optimize_loop(ops, expected)

        ops = """
        [i0]
        i1 = int_add(0, i0)
        jump(i1)
        """
        expected = """
        [i0]
        jump(i0)
        """
        self.optimize_loop(ops, expected)

        ops = """
        [i0]
        i1 = int_mul(0, i0)
        jump(i1)
        """
        expected = """
        [i0]
        jump(0)
        """
        self.optimize_loop(ops, expected)

        ops = """
        [i0]
        i1 = int_mul(1, i0)
        jump(i1)
        """
        expected = """
        [i0]
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_fold_partially_constant_ops_ovf(self):
        ops = """
        [i0]
        i1 = int_sub_ovf(i0, 0)
        guard_no_overflow() []
        jump(i1)
        """
        expected = """
        [i0]
        jump(i0)
        """
        self.optimize_loop(ops, expected)

        ops = """
        [i0]
        i1 = int_add_ovf(i0, 0)
        guard_no_overflow() []
        jump(i1)
        """
        expected = """
        [i0]
        jump(i0)
        """
        self.optimize_loop(ops, expected)

        ops = """
        [i0]
        i1 = int_add_ovf(0, i0)
        guard_no_overflow() []
        jump(i1)
        """
        expected = """
        [i0]
        jump(i0)
        """
        self.optimize_loop(ops, expected)

        ops = """
        [i0]
        i1 = int_mul_ovf(0, i0)
        guard_no_overflow() []
        jump(i1)
        """
        expected = """
        [i0]
        jump(0)
        """
        self.optimize_loop(ops, expected)

        ops = """
        [i0]
        i1 = int_mul_ovf(i0, 0)
        guard_no_overflow() []
        jump(i1)
        """
        expected = """
        [i0]
        jump(0)
        """
        self.optimize_loop(ops, expected)

        ops = """
        [i0]
        i1 = int_mul_ovf(1, i0)
        guard_no_overflow() []
        jump(i1)
        """
        expected = """
        [i0]
        jump(i0)
        """
        self.optimize_loop(ops, expected)

        ops = """
        [i0]
        i1 = int_mul_ovf(i0, 1)
        guard_no_overflow() []
        jump(i1)
        """
        expected = """
        [i0]
        jump(i0)
        """
        self.optimize_loop(ops, expected)


    def test_guard_value_to_guard_true(self):
        ops = """
        [i]
        i1 = int_lt(i, 3)
        guard_value(i1, 1) [i]
        jump(i)
        """
        expected = """
        [i]
        i1 = int_lt(i, 3)
        guard_true(i1) [i]
        jump(i)
        """
        self.optimize_loop(ops, expected)

    def test_guard_value_to_guard_false(self):
        ops = """
        [i]
        i1 = int_is_true(i)
        guard_value(i1, 0) [i]
        jump(i)
        """
        expected = """
        [i]
        i1 = int_is_true(i)
        guard_false(i1) [i]
        jump(0)
        """
        self.optimize_loop(ops, expected)

    def test_guard_value_on_nonbool(self):
        ops = """
        [i]
        i1 = int_add(i, 3)
        guard_value(i1, 0) [i]
        jump(i)
        """
        expected = """
        [i]
        i1 = int_add(i, 3)
        guard_value(i1, 0) [i]
        jump(-3)
        """
        self.optimize_loop(ops, expected)

    def test_int_is_true_of_bool(self):
        ops = """
        [i0, i1]
        i2 = int_gt(i0, i1)
        i3 = int_is_true(i2)
        i4 = int_is_true(i3)
        guard_value(i4, 0) [i0, i1]
        jump(i0, i1)
        """
        expected = """
        [i0, i1]
        i2 = int_gt(i0, i1)
        guard_false(i2) [i0, i1]
        jump(i0, i1)
        """
        self.optimize_loop(ops, expected)


    def test_constant_boolrewrite_lt(self):
        ops = """
        [i0]
        i1 = int_lt(i0, 0)
        guard_true(i1) []
        i2 = int_ge(i0, 0)
        guard_false(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_lt(i0, 0)
        guard_true(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_constant_boolrewrite_gt(self):
        ops = """
        [i0]
        i1 = int_gt(i0, 0)
        guard_true(i1) []
        i2 = int_le(i0, 0)
        guard_false(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_gt(i0, 0)
        guard_true(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_constant_boolrewrite_reflex(self):
        ops = """
        [i0]
        i1 = int_gt(i0, 0)
        guard_true(i1) []
        i2 = int_lt(0, i0)
        guard_true(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_gt(i0, 0)
        guard_true(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_constant_boolrewrite_reflex_invers(self):
        ops = """
        [i0]
        i1 = int_gt(i0, 0)
        guard_true(i1) []
        i2 = int_ge(0, i0)
        guard_false(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_gt(i0, 0)
        guard_true(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_remove_consecutive_guard_value_constfold(self):
        ops = """
        [i0]
        guard_value(i0, 0) []
        i1 = int_add(i0, 1)
        guard_value(i1, 1) []
        i2 = int_add(i1, 2)
        jump(i2)
        """
        expected = """
        [i0]
        guard_value(i0, 0) []
        jump(3)
        """
        self.optimize_loop(ops, expected)

    def test_bound_lt(self):
        ops = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_true(i1) []
        i2 = int_lt(i0, 5)
        guard_true(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_true(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_lt_noguard(self):
        ops = """
        [i0]
        i1 = int_lt(i0, 4)
        i2 = int_lt(i0, 5)
        jump(i2)
        """
        expected = """
        [i0]
        i1 = int_lt(i0, 4)
        i2 = int_lt(i0, 5)
        jump(i2)
        """
        self.optimize_loop(ops, expected)

    def test_bound_lt_noopt(self):
        ops = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_false(i1) []
        i2 = int_lt(i0, 5)
        guard_true(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_false(i1) []
        i2 = int_lt(i0, 5)
        guard_true(i2) []
        jump(4)
        """
        self.optimize_loop(ops, expected)

    def test_bound_lt_rev(self):
        ops = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_false(i1) []
        i2 = int_gt(i0, 3)
        guard_true(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_false(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_lt_tripple(self):
        ops = """
        [i0]
        i1 = int_lt(i0, 0)
        guard_true(i1) []
        i2 = int_lt(i0, 7)
        guard_true(i2) []
        i3 = int_lt(i0, 5)
        guard_true(i3) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_lt(i0, 0)
        guard_true(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_lt_add(self):
        ops = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_true(i1) []
        i2 = int_add(i0, 10)
        i3 = int_lt(i2, 15)
        guard_true(i3) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_true(i1) []
        i2 = int_add(i0, 10)
        jump(i0)
        """
        self.optimize_loop(ops, expected)

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
        jump()
        """ % (MININT, )
        expected = """
        [i0]
        i1 = int_lt(i0, 0)
        guard_true(i1) []
        i2 = int_eq(i0, %s)
        guard_false(i2) []
        i3 = int_neg(i0)
        jump()
        """ % (MININT, )
        self.optimize_loop(ops, expected)

    def test_bound_lt_add_ovf(self):
        ops = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_true(i1) []
        i2 = int_add_ovf(i0, 10)
        guard_no_overflow() []
        i3 = int_lt(i2, 15)
        guard_true(i3) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_true(i1) []
        i2 = int_add(i0, 10)
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_lt_sub(self):
        ops = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_true(i1) []
        i1p = int_gt(i0, -4)
        guard_true(i1p) []
        i2 = int_sub(i0, 10)
        i3 = int_lt(i2, -5)
        guard_true(i3) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_true(i1) []
        i1p = int_gt(i0, -4)
        guard_true(i1p) []
        i2 = int_sub(i0, 10)
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_lt_sub_before(self):
        ops = """
        [i0]
        i2 = int_sub(i0, 10)
        i3 = int_lt(i2, -5)
        guard_true(i3) []
        i1 = int_lt(i0, 5)
        guard_true(i1) []
        jump(i0)
        """
        expected = """
        [i0]
        i2 = int_sub(i0, 10)
        i3 = int_lt(i2, -5)
        guard_true(i3) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_ltle(self):
        ops = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_true(i1) []
        i2 = int_le(i0, 3)
        guard_true(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_lt(i0, 4)
        guard_true(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_lelt(self):
        ops = """
        [i0]
        i1 = int_le(i0, 4)
        guard_true(i1) []
        i2 = int_lt(i0, 5)
        guard_true(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_le(i0, 4)
        guard_true(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_gt(self):
        ops = """
        [i0]
        i1 = int_gt(i0, 5)
        guard_true(i1) []
        i2 = int_gt(i0, 4)
        guard_true(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_gt(i0, 5)
        guard_true(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_gtge(self):
        ops = """
        [i0]
        i1 = int_gt(i0, 5)
        guard_true(i1) []
        i2 = int_ge(i0, 6)
        guard_true(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_gt(i0, 5)
        guard_true(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_gegt(self):
        ops = """
        [i0]
        i1 = int_ge(i0, 5)
        guard_true(i1) []
        i2 = int_gt(i0, 4)
        guard_true(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_ge(i0, 5)
        guard_true(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_ovf(self):
        ops = """
        [i0]
        i1 = int_ge(i0, 0)
        guard_true(i1) []
        i2 = int_lt(i0, 10)
        guard_true(i2) []
        i3 = int_add_ovf(i0, 1)
        guard_no_overflow() []
        jump(i3)
        """
        expected = """
        [i0]
        i1 = int_ge(i0, 0)
        guard_true(i1) []
        i2 = int_lt(i0, 10)
        guard_true(i2) []
        i3 = int_add(i0, 1)
        jump(i3)
        """
        self.optimize_loop(ops, expected)

    def test_addsub_int(self):
        ops = """
        [i0, i10]
        i1 = int_add(i0, i10)
        i2 = int_sub(i1, i10)
        i3 = int_add(i2, i10)
        i4 = int_add(i2, i3)
        jump(i4, i10)
        """
        expected = """
        [i0, i10]
        i1 = int_add(i0, i10)
        i4 = int_add(i0, i1)
        jump(i4, i10)
        """
        self.optimize_loop(ops, expected)

    def test_addsub_int2(self):
        ops = """
        [i0, i10]
        i1 = int_add(i10, i0)
        i2 = int_sub(i1, i10)
        i3 = int_add(i10, i2)
        i4 = int_add(i2, i3)
        jump(i4, i10)
        """
        expected = """
        [i0, i10]
        i1 = int_add(i10, i0)
        i4 = int_add(i0, i1)
        jump(i4, i10)
        """
        self.optimize_loop(ops, expected)

    def test_int_add_commutative(self):
        ops = """
        [i0, i1]
        i2 = int_add(i0, i1)
        i3 = int_add(i1, i0)
        jump(i2, i3)
        """
        expected = """
        [i0, i1]
        i2 = int_add(i0, i1)
        jump(i2, i2)
        """
        self.optimize_loop(ops, expected)

    def test_addsub_const(self):
        ops = """
        [i0]
        i1 = int_add(i0, 1)
        i2 = int_sub(i1, 1)
        i3 = int_add(i2, 1)
        jump(i2, i3)
        """
        expected = """
        [i0]
        i1 = int_add(i0, 1)
        jump(i0, i1)
        """
        self.optimize_loop(ops, expected)

    def test_int_add_sub_constants_inverse(self):
        ops = """
        [i0, i10, i11, i12, i13]
        i2 = int_add(1, i0)
        i3 = int_add(-1, i2)
        i4 = int_sub(i0, -1)
        i5 = int_sub(i0, i2)
        jump(i0, i2, i3, i4, i5)
        """
        expected = """
        [i0, i10, i11, i12, i13]
        i2 = int_add(1, i0)
        jump(i0, i2, i0, i2, -1)
        """
        self.optimize_loop(ops, expected)
        ops = """
        [i0, i10, i11, i12, i13]
        i2 = int_add(i0, 1)
        i3 = int_add(-1, i2)
        i4 = int_sub(i0, -1)
        i5 = int_sub(i0, i2)
        jump(i0, i2, i3, i4, i5)
        """
        expected = """
        [i0, i10, i11, i12, i13]
        i2 = int_add(i0, 1)
        jump(i0, i2, i0, i2, -1)
        """
        self.optimize_loop(ops, expected)

        ops = """
        [i0, i10, i11, i12, i13, i14]
        i2 = int_sub(i0, 1)
        i3 = int_add(-1, i0)
        i4 = int_add(i0, -1)
        i5 = int_sub(i2, -1)
        i6 = int_sub(i2, i0)
        jump(i0, i2, i3, i4, i5, i6)
        """
        expected = """
        [i0, i10, i11, i12, i13, i14]
        i2 = int_sub(i0, 1)
        jump(i0, i2, i2, i2, i0, -1)
        """
        self.optimize_loop(ops, expected)
        ops = """
        [i0, i10, i11, i12]
        i2 = int_add(%s, i0)
        i3 = int_add(i2, %s)
        i4 = int_sub(i0, %s)
        jump(i0, i2, i3, i4)
        """ % ((MININT, ) * 3)
        expected = """
        [i0, i10, i11, i12]
        i2 = int_add(%s, i0)
        i4 = int_sub(i0, %s)
        jump(i0, i2, i0, i4)
        """ % ((MININT, ) * 2)
        self.optimize_loop(ops, expected)

    def test_addsub_ovf(self):
        ops = """
        [i0]
        i1 = int_add_ovf(i0, 10)
        guard_no_overflow() []
        i2 = int_sub_ovf(i1, 5)
        guard_no_overflow() []
        jump(i2)
        """
        expected = """
        [i0]
        i1 = int_add_ovf(i0, 10)
        guard_no_overflow() []
        i2 = int_sub(i1, 5)
        jump(i2)
        """
        self.optimize_loop(ops, expected)

    def test_subadd_ovf(self):
        ops = """
        [i0]
        i1 = int_sub_ovf(i0, 10)
        guard_no_overflow() []
        i2 = int_add_ovf(i1, 5)
        guard_no_overflow() []
        jump(i2)
        """
        expected = """
        [i0]
        i1 = int_sub_ovf(i0, 10)
        guard_no_overflow() []
        i2 = int_add(i1, 5)
        jump(i2)
        """
        self.optimize_loop(ops, expected)

    def test_sub_identity(self):
        ops = """
        [i0]
        i1 = int_sub(i0, i0)
        i2 = int_sub(i1, i0)
        jump(i1, i2)
        """
        expected = """
        [i0]
        i2 = int_neg(i0)
        jump(0, i2)
        """
        self.optimize_loop(ops, expected)

    def test_shift_zero(self):
        ops = """
        [i0]
        i1 = int_lshift(0, i0)
        i2 = int_rshift(0, i0)
        i3 = int_lshift(i0, 0)
        i4 = int_rshift(i0, 0)
        jump(i1, i2, i3, i4)
        """
        expected = """
        [i0]
        jump(0, 0, i0, i0)
        """
        self.optimize_loop(ops, expected)

    def test_ushift_zero(self):
        ops = """
        [i0]
        i2 = uint_rshift(0, i0)
        i4 = uint_rshift(i0, 0)
        jump(i2, i4)
        """
        expected = """
        [i0]
        jump(0, i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_and(self):
        ops = """
        [i0]
        i1 = int_and(i0, 255)
        i2 = int_lt(i1, 500)
        guard_true(i2) []
        i3 = int_le(i1, 255)
        guard_true(i3) []
        i4 = int_gt(i1, -1)
        guard_true(i4) []
        i5 = int_ge(i1, 0)
        guard_true(i5) []
        i6 = int_lt(i1, 0)
        guard_false(i6) []
        i7 = int_le(i1, -1)
        guard_false(i7) []
        i8 = int_gt(i1, 255)
        guard_false(i8) []
        i9 = int_ge(i1, 500)
        guard_false(i9) []
        jump(i1)
        """
        expected = """
        [i0]
        i1 = int_and(i0, 255)
        jump(i1)
        """
        self.optimize_loop(ops, expected)

    def test_bug_int_and_1(self):
        ops = """
        [i51]
        i1 = int_ge(i51, 0)
        guard_true(i1) []
        i57 = int_and(i51, 1)
        i62 = int_eq(i57, 0)
        guard_false(i62) []
        """
        self.optimize_loop(ops, ops)

    def test_bug_int_and_2(self):
        ops = """
        [i51]
        i1 = int_ge(i51, 0)
        guard_true(i1) []
        i57 = int_and(4, i51)
        i62 = int_eq(i57, 0)
        guard_false(i62) []
        """
        self.optimize_loop(ops, ops)

    def test_bug_int_or(self):
        ops = """
        [i51, i52]
        i1 = int_ge(i51, 0)
        guard_true(i1) []
        i2 = int_ge(i52, 0)
        guard_true(i2) []
        i57 = int_or(i51, i52)
        i62 = int_eq(i57, 0)
        guard_false(i62) []
        """
        self.optimize_loop(ops, ops)

    def test_int_and_positive(self):
        ops = """
        [i51, i52]
        i1 = int_ge(i51, 0)
        guard_true(i1) []
        i2 = int_ge(i52, 0)
        guard_true(i2) []

        i57 = int_and(i51, i52)
        i62 = int_lt(i57, 0)
        guard_false(i62) []
        jump(i57)
        """
        expected = """
        [i51, i52]
        i1 = int_ge(i51, 0)
        guard_true(i1) []
        i2 = int_ge(i52, 0)
        guard_true(i2) []

        i57 = int_and(i51, i52)
        jump(i57)
        """
        self.optimize_loop(ops, expected)

    def test_int_or_positive(self):
        ops = """
        [i51, i52]
        i1 = int_ge(i51, 0)
        guard_true(i1) []
        i2 = int_ge(i52, 0)
        guard_true(i2) []

        i57 = int_or(i51, i52)
        i62 = int_lt(i57, 0)
        guard_false(i62) []
        jump(i57)
        """
        expected = """
        [i51, i52]
        i1 = int_ge(i51, 0)
        guard_true(i1) []
        i2 = int_ge(i52, 0)
        guard_true(i2) []

        i57 = int_or(i51, i52)
        jump(i57)
        """
        self.optimize_loop(ops, expected)

    def test_subsub_ovf(self):
        ops = """
        [i0]
        i1 = int_sub_ovf(1, i0)
        guard_no_overflow() []
        i2 = int_gt(i1, 1)
        guard_true(i2) []
        i3 = int_sub_ovf(1, i0)
        guard_no_overflow() []
        i4 = int_gt(i3, 1)
        guard_true(i4) []
        jump(i0)
        """
        expected = """
        [i0]
        i1 = int_sub_ovf(1, i0)
        guard_no_overflow() []
        i2 = int_gt(i1, 1)
        guard_true(i2) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_eq(self):
        ops = """
        [i0, i1]
        i2 = int_le(i0, 4)
        guard_true(i2) []
        i3 = int_eq(i0, i1)
        guard_true(i3) []
        i4 = int_lt(i1, 5)
        guard_true(i4) []
        jump(i0, i1)
        """
        expected = """
        [i0, i1]
        i2 = int_le(i0, 4)
        guard_true(i2) []
        i3 = int_eq(i0, i1)
        guard_true(i3) []
        jump(i0, i1)
        """
        self.optimize_loop(ops, expected)

    def test_bound_eq_const(self):
        ops = """
        [i0]
        i1 = int_eq(i0, 7)
        guard_true(i1) []
        i2 = int_add(i0, 3)
        jump(i2)
        """
        expected = """
        [i0]
        i1 = int_eq(i0, 7)
        guard_true(i1) []
        jump(10)

        """
        self.optimize_loop(ops, expected)

    def test_bound_eq_const_not(self):
        ops = """
        [i0]
        i1 = int_eq(i0, 7)
        guard_false(i1) []
        i2 = int_add(i0, 3)
        jump(i2)
        """
        expected = """
        [i0]
        i1 = int_eq(i0, 7)
        guard_false(i1) []
        i2 = int_add(i0, 3)
        jump(i2)

        """
        self.optimize_loop(ops, expected)

    def test_bound_ne_const(self):
        ops = """
        [i0]
        i1 = int_ne(i0, 7)
        guard_false(i1) []
        i2 = int_add(i0, 3)
        jump(i2)
        """
        expected = """
        [i0]
        i1 = int_ne(i0, 7)
        guard_false(i1) []
        jump(10)

        """
        self.optimize_loop(ops, expected)

    def test_bound_ne_const_not(self):
        ops = """
        [i0]
        i1 = int_ne(i0, 7)
        guard_true(i1) []
        i2 = int_add(i0, 3)
        jump(i2)
        """
        expected = """
        [i0]
        i1 = int_ne(i0, 7)
        guard_true(i1) []
        i2 = int_add(i0, 3)
        jump(i2)
        """
        self.optimize_loop(ops, expected)

    def test_bound_ltne(self):
        ops = """
        [i0, i1]
        i2 = int_lt(i0, 7)
        guard_true(i2) []
        i3 = int_ne(i0, 10)
        guard_true(i2) []
        jump(i0, i1)
        """
        expected = """
        [i0, i1]
        i2 = int_lt(i0, 7)
        guard_true(i2) []
        jump(i0, i1)
        """
        self.optimize_loop(ops, expected)

    def test_bound_lege_const(self):
        ops = """
        [i0]
        i1 = int_ge(i0, 7)
        guard_true(i1) []
        i2 = int_le(i0, 7)
        guard_true(i2) []
        i3 = int_add(i0, 3)
        jump(i3)
        """
        expected = """
        [i0]
        i1 = int_ge(i0, 7)
        guard_true(i1) []
        i2 = int_le(i0, 7)
        guard_true(i2) []
        jump(10)

        """
        self.optimize_loop(ops, expected)

    def test_mul_ovf(self):
        ops = """
        [i0, i1]
        i2 = int_and(i0, 255)
        i3 = int_lt(i1, 5)
        guard_true(i3) []
        i4 = int_gt(i1, -10)
        guard_true(i4) []
        i5 = int_mul_ovf(i2, i1)
        guard_no_overflow() []
        i6 = int_lt(i5, -2550)
        guard_false(i6) []
        i7 = int_ge(i5, 1276)
        guard_false(i7) []
        i8 = int_gt(i5, 126)
        guard_true(i8) []
        jump(i0, i1)
        """
        expected = """
        [i0, i1]
        i2 = int_and(i0, 255)
        i3 = int_lt(i1, 5)
        guard_true(i3) []
        i4 = int_gt(i1, -10)
        guard_true(i4) []
        i5 = int_mul(i2, i1)
        i8 = int_gt(i5, 126)
        guard_true(i8) []
        jump(i0, i1)
        """
        self.optimize_loop(ops, expected)


    def test_sub_ovf_before(self):
        ops = """
        [i0, i1]
        i2 = int_and(i0, 255)
        i3 = int_sub_ovf(i2, i1)
        guard_no_overflow() []
        i4 = int_le(i3, 10)
        guard_true(i4) []
        i5 = int_ge(i3, 2)
        guard_true(i5) []
        i6 = int_lt(i1, -10)
        guard_false(i6) []
        i7 = int_gt(i1, 253)
        guard_false(i7) []
        jump(i0, i1)
        """
        expected = """
        [i0, i1]
        i2 = int_and(i0, 255)
        i3 = int_sub_ovf(i2, i1)
        guard_no_overflow() []
        i4 = int_le(i3, 10)
        guard_true(i4) []
        i5 = int_ge(i3, 2)
        guard_true(i5) []
        jump(i0, i1)
        """
        self.optimize_loop(ops, expected)

    def test_int_is_true_bounds(self):
        ops = """
        [i0]
        i12 = int_ge(i0, 0)
        guard_true(i12) []
        i1 = int_is_true(i0)
        guard_true(i1) []
        i2 = int_ge(0, i0)
        guard_false(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i12 = int_ge(i0, 0)
        guard_true(i12) []
        i1 = int_is_true(i0)
        guard_true(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_int_is_zero_bounds(self):
        ops = """
        [i0]
        i12 = int_ge(i0, 0)
        guard_true(i12) []
        i1 = int_is_zero(i0)
        guard_false(i1) []
        i2 = int_ge(0, i0)
        guard_false(i2) []
        jump(i0)
        """
        expected = """
        [i0]
        i12 = int_ge(i0, 0)
        guard_true(i12) []
        i1 = int_is_zero(i0)
        guard_false(i1) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_int_or_same_arg(self):
        ops = """
        [i0]
        i1 = int_or(i0, i0)
        jump(i1)
        """
        expected = """
        [i0]
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    # ______________________________________________________

    def test_intand_1mask_covering_bitrange(self):
        ops = """
        [i0]
        i0pos = int_ge(i0, 0)
        guard_true(i0pos) []
        i0small = int_lt(i0, 256)
        guard_true(i0small) []
        i1 = int_and(i0, 255)
        i2 = int_and(i1, -1)
        i3 = int_and(511, i2)
        jump(i3)
        """

        expected = """
        [i0]
        i0pos = int_ge(i0, 0)
        guard_true(i0pos) []
        i0small = int_lt(i0, 256)
        guard_true(i0small) []
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_intand_maskwith0_in_bitrange(self):
        ops = """
        [i0, i2]
        i0pos = int_ge(i0, 0)
        guard_true(i0pos) []
        i0small = int_lt(i0, 256)
        guard_true(i0small) []

        i1 = int_and(i0, 257)

        i2pos = int_ge(i2, 0)
        guard_true(i2pos) []
        i2small = int_lt(i2, 256)
        guard_true(i2small) []

        i3 = int_and(259, i2)
        jump(i1, i3)
        """
        self.optimize_loop(ops, ops)

    i0_range_256_i1_range_65536_prefix = """
        [i0, i1]
        i0pos = int_ge(i0, 0)
        guard_true(i0pos) []
        i0small = int_lt(i0, 256)
        guard_true(i0small) []

        i1pos = int_ge(i1, 0)
        guard_true(i1pos) []
        i1small = int_lt(i1, 65536)
        guard_true(i1small) []
    """

    def test_int_and_cmp_above_bounds(self):

        ops = self.i0_range_256_i1_range_65536_prefix + """
        i2 = int_and(i0, i1)
        i3 = int_le(i2, 255)
        guard_true(i3) []
        jump(i2)
        """

        expected = self.i0_range_256_i1_range_65536_prefix + """
        i2 = int_and(i0, i1)
        jump(i2)
        """
        self.optimize_loop(ops, expected)

    def test_int_and_cmp_below_bounds(self):
        ops = self.i0_range_256_i1_range_65536_prefix + """
        i2 = int_and(i0, i1)
        i3 = int_lt(i2, 255)
        guard_true(i3) []
        jump(i2)
        """
        self.optimize_loop(ops, ops)

    def test_int_and_positive(self):
        ops = """
        [i0, i1]
        i2 = int_ge(i1, 0)
        guard_true(i2) []
        i3 = int_and(i0, i1)
        i4 = int_ge(i3, 0)
        guard_true(i4) []
        jump(i3)
        """
        expected = """
        [i0, i1]
        i2 = int_ge(i1, 0)
        guard_true(i2) []
        i3 = int_and(i0, i1)
        jump(i3)
        """
        self.optimize_loop(ops, expected)

    def test_int_or_cmp_above_bounds(self):
        ops = self.i0_range_256_i1_range_65536_prefix + """
        i2 = int_or(i0, i1)
        i3 = int_le(i2, 65535)
        guard_true(i3) []
        jump(i2)
        """

        expected = self.i0_range_256_i1_range_65536_prefix + """
        i2 = int_or(i0, i1)
        jump(i2)
        """
        self.optimize_loop(ops, expected)

    def test_int_or_cmp_below_bounds(self):
        ops = self.i0_range_256_i1_range_65536_prefix + """
        i2 = int_or(i0, i1)
        i3 = int_lt(i2, 65535)
        guard_true(i3) []
        jump(i2)
        """
        self.optimize_loop(ops, ops)

    def test_int_xor_cmp_above_bounds(self):
        ops = self.i0_range_256_i1_range_65536_prefix + """
        i2 = int_xor(i0, i1)
        i3 = int_le(i2, 65535)
        guard_true(i3) []
        jump(i2)
        """

        expected = self.i0_range_256_i1_range_65536_prefix + """
        i2 = int_xor(i0, i1)
        jump(i2)
        """
        self.optimize_loop(ops, expected)

    def test_int_xor_cmp_below_bounds(self):
        ops = self.i0_range_256_i1_range_65536_prefix + """
        i2 = int_xor(i0, i1)
        i3 = int_lt(i2, 65535)
        guard_true(i3) []
        jump(i2)
        """
        self.optimize_loop(ops, ops)

    def test_int_xor_positive_is_positive(self):
        ops = """
        [i0, i1]
        i2 = int_lt(i0, 0)
        guard_false(i2) []
        i3 = int_lt(i1, 0)
        guard_false(i3) []
        i4 = int_xor(i0, i1)
        i5 = int_lt(i4, 0)
        guard_false(i5) []
        jump(i4, i0)
        """
        expected = """
        [i0, i1]
        i2 = int_lt(i0, 0)
        guard_false(i2) []
        i3 = int_lt(i1, 0)
        guard_false(i3) []
        i4 = int_xor(i0, i1)
        jump(i4, i0)
        """
        self.optimize_loop(ops, expected)

    def test_positive_rshift_bits_minus_1(self):
        ops = """
        [i0]
        i2 = int_lt(i0, 0)
        guard_false(i2) []
        i3 = int_rshift(i2, %d)
        jump(i3)
        """ % (LONG_BIT - 1,)
        expected = """
        [i0]
        i2 = int_lt(i0, 0)
        guard_false(i2) []
        jump(0)
        """
        self.optimize_loop(ops, expected)

    def test_int_invert(self):
        ops = """
        [i0]
        i1 = int_lt(i0, 0)
        guard_false(i1) []
        i2 = int_invert(i0)
        i3 = int_lt(i2, 0)
        guard_true(i3) []
        jump(i2)
        """
        expected = """
        [i0]
        i1 = int_lt(i0, 0)
        guard_false(i1) []
        i2 = int_invert(i0)
        jump(i2)
        """
        self.optimize_loop(ops, expected)

    def test_int_invert_invert(self):
        ops = """
        [i1]
        i2 = int_invert(i1)
        i3 = int_invert(i2)
        jump(i3)
        """
        expected = """
        [i1]
        i2 = int_invert(i1)
        jump(i1)
        """
        self.optimize_loop(ops, expected)

    def test_int_invert_postprocess(self):
        ops = """
        [i1]
        i2 = int_invert(i1)
        i3 = int_lt(i2, 0)
        guard_true(i3) []
        i4 = int_ge(i1, 0)
        guard_true(i4) []
        jump(i2)
        """
        expected = """
        [i1]
        i2 = int_invert(i1)
        i3 = int_lt(i2, 0)
        guard_true(i3) []
        jump(i2)
        """
        self.optimize_loop(ops, expected)

    def test_int_neg(self):
        ops = """
        [i0]
        i1 = int_lt(i0, 0)
        guard_false(i1) []
        i2 = int_neg(i0)
        i3 = int_le(i2, 0)
        guard_true(i3) []
        jump(i2)
        """
        expected = """
        [i0]
        i1 = int_lt(i0, 0)
        guard_false(i1) []
        i2 = int_neg(i0)
        jump(i2)
        """
        self.optimize_loop(ops, expected)

    def test_int_neg_postprocess(self):
        ops = """
        [i1]
        i2 = int_neg(i1)
        i3 = int_ge(i2, 0)
        guard_true(i3) []
        i4 = int_le(i1, 0)
        guard_true(i4) []
        jump(i1)
        """
        expected = """
        [i1]
        i2 = int_neg(i1)
        i3 = int_ge(i2, 0)
        guard_true(i3) []
        jump(i1)
        """
        self.optimize_loop(ops, expected)

    def test_int_signext_already_in_bounds(self):
        ops = """
        [i0]
        i1 = int_signext(i0, 1)
        i2 = int_signext(i1, 2)
        jump(i2)
        """
        expected = """
        [i0]
        i1 = int_signext(i0, 1)
        jump(i1)
        """
        self.optimize_loop(ops, expected)
        #
        ops = """
        [i0]
        i1 = int_signext(i0, 1)
        i2 = int_signext(i1, 1)
        jump(i2)
        """
        expected = """
        [i0]
        i1 = int_signext(i0, 1)
        jump(i1)
        """
        self.optimize_loop(ops, expected)
        #
        ops = """
        [i0]
        i1 = int_signext(i0, 2)
        i2 = int_signext(i1, 1)
        jump(i2)
        """
        self.optimize_loop(ops, ops)

    def test_bound_backpropagate_int_signext(self):
        ops = """
        [i0]
        i1 = int_signext(i0, 1)
        i2 = int_eq(i0, i1)
        guard_true(i2) []
        i3 = int_le(i0, 127)    # implied by equality with int_signext
        guard_true(i3) []
        i5 = int_gt(i0, -129)   # implied by equality with int_signext
        guard_true(i5) []
        jump(i1)
        """
        expected = """
        [i0]
        i1 = int_signext(i0, 1)
        i2 = int_eq(i0, i1)
        guard_true(i2) []
        jump(i1)
        """
        self.optimize_loop(ops, expected)

    def test_bound_backpropagate_int_signext_2(self):
        ops = """
        [i0]
        i1 = int_signext(i0, 1)
        i2 = int_eq(i0, i1)
        guard_true(i2) []
        i3 = int_le(i0, 126)    # false for i1 == 127
        guard_true(i3) []
        i5 = int_gt(i0, -128)   # false for i1 == -128
        guard_true(i5) []
        jump(i1)
        """
        self.optimize_loop(ops, ops)

    def test_uint_mul_high_constfold(self):
        ops = """
        [i0]
        i1 = int_lshift(254, %s)
        i2 = int_lshift(171, %s)
        i3 = uint_mul_high(i1, i2)
        jump(i3)
        """ % (LONG_BIT // 2, LONG_BIT // 2)
        expected = """
        [i0]
        jump(43434)
        """
        self.optimize_loop(ops, expected)

    def test_mul_ovf_before_bug(self):
        ops = """
        [i0]
        i3 = int_mul(i0, 12)
        guard_value(i3, 12) []
        jump(i0)
        """
        self.optimize_loop(ops, ops)

    def test_lshift_before_bug(self):
        ops = """
        [i0]
        i3 = int_lshift(%s, i0)

        i1 = int_lt(i0, 16)
        guard_true(i1) []
        i2 = int_ge(i0, 0)
        guard_true(i2) []

        guard_value(i3, 0) []
        jump(i0)
        """ % (1 << (LONG_BIT - 3))
        self.optimize_loop(ops, ops)


    def test_bug_dont_use_getint(self):
        ops = """
        [i1, i2]
        i45 = int_xor(i1, i2) # 0
        i163 = int_neg(i45) # 0
        guard_value(i163, 0) []
        i228 = int_add(1, i2)
        i318 = uint_rshift(i228, 0) # == i288
        i404 = int_add(i318, i45)
        finish(i404)
        """
        expected = """
        [i1, i2]
        i45 = int_xor(i1, i2) # 0
        i163 = int_neg(i45) # 0
        guard_value(i163, 0) []
        i404 = int_add(1, i2)
        finish(i404)
        """
        self.optimize_loop(ops, expected)

    def test_bound_lshift_result_unbounded(self):
        # bounded_above << bounded
        ops = """
        [i1, i2, i3]
        i4 = int_lt(i1, 7) # i1 < 7
        guard_true(i4) []

        i5 = int_lt(i3, 2) # i3 == 0 or i3 == 1
        guard_true(i5) []
        i6 = int_ge(i3, 0)
        guard_true(i6) []

        i7 = int_lshift(i1, i3)
        i8 = int_le(i7, 14)
        guard_true(i8) [] # can't be removed
        i8b = int_lshift(i1, i2)
        i9 = int_le(i8b, 14) # can't be removed
        guard_true(i9) []
        jump(i1, i2, i3)
        """
        self.optimize_loop(ops, ops)

        # bounded << unbounded
        ops = """
        [i1b, i2]
        i4b = int_lt(i1b, 7) # 0 <= i1b < 7
        guard_true(i4b) []
        i4c = int_ge(i1b, 0)
        guard_true(i4c) []

        i15 = int_lshift(i1b, i2)
        i16 = int_le(i15, 14)
        guard_true(i16) []
        jump(i1b, i2)
        """
        self.optimize_loop(ops, ops)

    def test_bound_lshift(self):
        ops = """
        [i1b, i3]
        i4b = int_lt(i1b, 7) # 0 <= i1b < 7
        guard_true(i4b) []
        i4c = int_ge(i1b, 0)
        guard_true(i4c) []

        i5 = int_lt(i3, 2) # i3 == 0 or i3 == 1
        guard_true(i5) []
        i6 = int_ge(i3, 0)
        guard_true(i6) []

        i13 = int_lshift(i1b, i3)
        i14 = int_le(i13, 14) # removed
        guard_true(i14) [] # removed
        jump(i1b, i3)
        """
        expected = """
        [i1b, i3]
        i4b = int_lt(i1b, 7)
        guard_true(i4b) []
        i4c = int_ge(i1b, 0)
        guard_true(i4c) []

        i5 = int_lt(i3, 2)
        guard_true(i5) []
        i6 = int_ge(i3, 0)
        guard_true(i6) []

        i13 = int_lshift(i1b, i3)
        jump(i1b, i3)
        """
        self.optimize_loop(ops, expected)

    def test_bound_lshift_backwards(self):
        ops = """
        [i0, i3]
        i5 = int_lt(i3, 2) # i3 == 0 or i3 == 1
        guard_true(i5) []
        i6 = int_ge(i3, 0)
        guard_true(i6) []

        i10 = int_lshift(i0, i3)
        i11 = int_le(i10, 14)
        guard_true(i11) []
        i12 = int_lt(i0, 15) # used to be removed, but that's wrong
        guard_true(i12) []

        jump(i0, i3)
        """
        expected = """
        [i0, i3]

        i5 = int_lt(i3, 2)
        guard_true(i5) []
        i6 = int_ge(i3, 0)
        guard_true(i6) []

        i10 = int_lshift(i0, i3)
        i11 = int_le(i10, 14)
        guard_true(i11) []
        i12 = int_lt(i0, 15) # used to be removed, but that's wrong
        guard_true(i12) []

        jump(i0, i3)
        """
        self.optimize_loop(ops, expected)

    def test_bound_rshift_result_unbounded(self):
        # unbounded >> bounded
        ops = """
        [i0, i3]
        i5 = int_lt(i3, 2) # i3 == 0 or i3 == 1
        guard_true(i5) []
        i6 = int_ge(i3, 0)
        guard_true(i6) []

        i10 = int_rshift(i0, i3)
        i11 = int_le(i10, 14)
        guard_true(i11) []
        i12 = int_lt(i0, 25)
        guard_true(i12) []
        jump(i0, i3)
        """
        self.optimize_loop(ops, ops)

    def test_bound_rshift(self):
        ops = """
        [i1, i1b, i2, i3]
        i4 = int_lt(i1, 7) # i1 < 7
        guard_true(i4) []

        i4b = int_lt(i1b, 7) # 0 <= i1b < 7
        guard_true(i4b) []
        i4c = int_ge(i1b, 0)
        guard_true(i4c) []

        i5 = int_lt(i3, 2) # i3 == 0 or i3 == 1
        guard_true(i5) []
        i6 = int_ge(i3, 0)
        guard_true(i6) []

        i7 = int_rshift(i1, i3)
        i8 = int_le(i7, 14) # removed
        guard_true(i8) [] # removed
        i8b = int_rshift(i1, i2)
        i9 = int_le(i8b, 14)
        guard_true(i9) []

        i13 = int_rshift(i1b, i3)
        i14 = int_le(i13, 14) # removed
        guard_true(i14) [] # removed
        i15 = int_rshift(i1b, i2)
        i16 = int_le(i15, 14)
        guard_true(i16) []
        jump(i1, i1b, i2, i3)
        """
        expected = """
        [i1, i1b, i2, i3]
        i4 = int_lt(i1, 7)
        guard_true(i4) []

        i4b = int_lt(i1b, 7)
        guard_true(i4b) []
        i4c = int_ge(i1b, 0)
        guard_true(i4c) []

        i5 = int_lt(i3, 2)
        guard_true(i5) []
        i6 = int_ge(i3, 0)
        guard_true(i6) []

        i7 = int_rshift(i1, i3)
        i8b = int_rshift(i1, i2)
        i9 = int_le(i8b, 14)
        guard_true(i9) []

        i13 = int_rshift(i1b, i3)
        i15 = int_rshift(i1b, i2)
        i16 = int_le(i15, 14)
        guard_true(i16) []
        jump(i1, i1b, i2, i3)
        """
        self.optimize_loop(ops, expected)

    def test_pure_ovf_bug_simple(self):
        ops = """
        [i1, i2]
        i3 = int_add(i2, i1)
        i4 = int_add_ovf(i2, i1)
        guard_no_overflow() []
        jump(i4)
        """
        self.optimize_loop(ops, ops)

    def test_pure_ovf_bug_with_arithmetic_rewrites(self):
        ops = """
        [i1, i2]
        i3 = int_add_ovf(i1, i2)
        guard_no_overflow() []
        i4 = int_sub_ovf(i3, i2)
        guard_no_overflow() []
        jump(i4)
        """
        self.optimize_loop(ops, ops)

    @pytest.mark.xfail() # this test is wrong! it fails in Z3
    def test_pure_ovf_bug_with_replacement(self):
        ops = """
        [i0, i1, i10, i11]
        i2 = int_sub_ovf(i0, i1)
        guard_no_overflow() []
        i3 = int_add(i2, i11)
        i4 = int_sub_ovf(i3, i11)
        guard_no_overflow() []
        jump(i4)
        """
        result = """
        [i0, i1, i10, i11]
        i2 = int_sub_ovf(i0, i1)
        guard_no_overflow() []
        i3 = int_add(i2, i11)
        jump(i2)
        """
        self.optimize_loop(ops, result)

    def test_intdiv_bounds(self):
        ops = """
        [i0, i1]
        i4 = int_ge(i1, 3)
        guard_true(i4) []
        i2 = call_pure_i(321, i0, i1, descr=int_py_div_descr)
        i3 = int_add_ovf(i2, 50)
        guard_no_overflow() []
        jump(i3, i1)
        """
        expected = """
        [i0, i1]
        i4 = int_ge(i1, 3)
        guard_true(i4) []
        i2 = call_i(321, i0, i1, descr=int_py_div_descr)
        i3 = int_add(i2, 50)
        jump(i3, i1)
        """
        self.optimize_loop(ops, expected)

    def test_intmod_bounds2(self):
        # same as above (2nd case), but all guards are shifted by one so
        # that they must stay
        ops = """
        [i9, i1]
        i5 = call_pure_i(321, i1, -12, descr=int_py_mod_descr)
        i6 = int_le(i5, -11)
        guard_false(i6) []
        i7 = int_gt(i5, -1)
        guard_false(i7) []
        jump(i5)
        """
        self.optimize_loop(ops, ops.replace('call_pure_i', 'call_i'))

    def test_intmod_bounds_bug1(self):
        ops = """
        [i0]
        i1 = call_pure_i(321, i0, %d, descr=int_py_mod_descr)
        i2 = int_eq(i1, 0)
        guard_false(i2) []
        finish()
        """ % (-(1<<(LONG_BIT-1)),)
        self.optimize_loop(ops, ops.replace('call_pure_i', 'call_i'))


    def test_intmod_pow2(self):
        # 'n % power-of-two' can always be turned into int_and(), even
        # if n is possibly negative.  That's by we handle 'int_py_mod'
        # and not C-like mod.
        ops = """
        [i0]
        i1 = call_pure_i(321, i0, 8, descr=int_py_mod_descr)
        finish(i1)
        """
        expected = """
        [i0]
        i1 = int_and(i0, 7)
        finish(i1)
        """
        self.optimize_loop(ops, expected)


class TestComplexIntOpts(BaseTestBasic):

    def test_intmod_bounds(self):
        ops = """
        [i0, i1]
        i2 = call_pure_i(321, i0, 12, descr=int_py_mod_descr)
        i3 = int_ge(i2, 12)
        guard_false(i3) []
        i4 = int_lt(i2, 0)
        guard_false(i4) []
        i5 = call_pure_i(321, i1, -12, descr=int_py_mod_descr)
        i6 = int_le(i5, -12)
        guard_false(i6) []
        i7 = int_gt(i5, 0)
        guard_false(i7) []
        jump(i2, i5)
        """
        kk, ii = magic_numbers(12)
        expected = """
        [i0, i1]
        i4 = int_rshift(i0, %d)
        i6 = int_xor(i0, i4)
        i8 = uint_mul_high(i6, %d)
        i9 = uint_rshift(i8, %d)
        i10 = int_xor(i9, i4)
        i11 = int_mul(i10, 12)
        i2 = int_sub(i0, i11)
        i5 = call_i(321, i1, -12, descr=int_py_mod_descr)
        jump(i2, i5)
        """ % (63 if MAXINT > 2**32 else 31, intmask(kk), ii)
        self.optimize_loop(ops, expected)

    def test_mul_ovf_before(self):
        ops = """
        [i0, i1]
        i2 = int_and(i0, 255)
        i22 = int_add(i2, 1)
        i3 = int_mul_ovf(i22, i1)
        guard_no_overflow() []
        i4 = int_lt(i3, 10)
        guard_true(i4) []
        i5 = int_gt(i3, 2)
        guard_true(i5) []
        i6 = int_lt(i1, 0)
        guard_false(i6) []
        jump(i0, i1)
        """
        expected = """
        [i0, i1]
        i2 = int_and(i0, 255)
        i22 = int_add(i2, 1)
        i3 = int_mul_ovf(i22, i1)
        guard_no_overflow() []
        i4 = int_lt(i3, 10)
        guard_true(i4) []
        i5 = int_gt(i3, 2)
        guard_true(i5) []
        jump(i0, i1)
        """
        self.optimize_loop(ops, expected)

    def test_bound_arraylen(self):
        ops = """
        [i0, p0]
        p1 = new_array(i0, descr=arraydescr)
        i1 = arraylen_gc(p1, descr=arraydescr)
        i2 = int_gt(i1, -1)
        guard_true(i2) []
        setarrayitem_gc(p0, 0, p1, descr=arraydescr)
        jump(i0, p0)
        """
        # The dead arraylen_gc will be eliminated by the backend.
        expected = """
        [i0, p0]
        p1 = new_array(i0, descr=arraydescr)
        i1 = arraylen_gc(p1, descr=arraydescr)
        setarrayitem_gc(p0, 0, p1, descr=arraydescr)
        jump(i0, p0)
        """
        self.optimize_loop(ops, expected)

    def test_bound_strlen(self):
        ops = """
        [p0]
        i0 = strlen(p0)
        i1 = int_ge(i0, 0)
        guard_true(i1) []
        jump(p0)
        """
        # The dead strlen will be eliminated be the backend.
        expected = """
        [p0]
        i0 = strlen(p0)
        jump(p0)
        """
        self.optimize_loop(ops, expected)

        ops = """
        [p0]
        i0 = unicodelen(p0)
        i1 = int_ge(i0, 0)
        guard_true(i1) []
        jump(p0)
        """
        # The dead unicodelen will be eliminated be the backend.
        expected = """
        [p0]
        i0 = unicodelen(p0)
        jump(p0)
        """
        self.optimize_loop(ops, expected)

    @pytest.mark.xfail()  # see comment about optimize_UINT in intbounds.py
    def test_bound_unsigned_lt(self):
        ops = """
        [i0]
        i2 = int_lt(i0, 10)
        guard_true(i2) []
        i3 = int_ge(i0, 0)
        guard_true(i3) []
        i4 = uint_lt(i0, 10)
        guard_true(i4) []
        jump()
        """
        expected = """
        [i0]
        i2 = int_lt(i0, 10)
        guard_true(i2) []
        i3 = int_ge(i0, 0)
        guard_true(i3) []
        jump()
        """
        self.optimize_loop(ops, expected)
        #
        ops = """
        [i0]
        i2 = int_lt(i0, 10)
        guard_true(i2) []
        i3 = int_ge(i0, 0)
        guard_true(i3) []
        i4 = uint_lt(i0, 9)
        guard_true(i4) []
        jump()
        """
        self.optimize_loop(ops, ops)

    @pytest.mark.xfail()  # see comment about optimize_UINT in intbounds.py
    def test_bound_unsigned_le(self):
        ops = """
        [i0]
        i2 = int_lt(i0, 10)
        guard_true(i2) []
        i3 = int_ge(i0, 0)
        guard_true(i3) []
        i4 = uint_le(i0, 9)
        guard_true(i4) []
        jump()
        """
        expected = """
        [i0]
        i2 = int_lt(i0, 10)
        guard_true(i2) []
        i3 = int_ge(i0, 0)
        guard_true(i3) []
        jump()
        """
        self.optimize_loop(ops, expected)
        #
        ops = """
        [i0]
        i2 = int_lt(i0, 10)
        guard_true(i2) []
        i3 = int_ge(i0, 0)
        guard_true(i3) []
        i4 = uint_le(i0, 8)
        guard_true(i4) []
        jump()
        """
        self.optimize_loop(ops, ops)

    @pytest.mark.xfail()  # see comment about optimize_UINT in intbounds.py
    def test_bound_unsigned_gt(self):
        ops = """
        [i0]
        i2 = int_lt(i0, 10)
        guard_true(i2) []
        i3 = int_ge(i0, 0)
        guard_true(i3) []
        i4 = uint_gt(10, i0)
        guard_true(i4) []
        jump()
        """
        expected = """
        [i0]
        i2 = int_lt(i0, 10)
        guard_true(i2) []
        i3 = int_ge(i0, 0)
        guard_true(i3) []
        jump()
        """
        self.optimize_loop(ops, expected)
        #
        ops = """
        [i0]
        i2 = int_lt(i0, 10)
        guard_true(i2) []
        i3 = int_ge(i0, 0)
        guard_true(i3) []
        i4 = uint_gt(9, i0)
        guard_true(i4) []
        jump()
        """
        self.optimize_loop(ops, ops)

    @pytest.mark.xfail()  # see comment about optimize_UINT in intbounds.py
    def test_bound_unsigned_ge(self):
        ops = """
        [i0]
        i2 = int_lt(i0, 10)
        guard_true(i2) []
        i3 = int_ge(i0, 0)
        guard_true(i3) []
        i4 = uint_ge(9, i0)
        guard_true(i4) []
        jump()
        """
        expected = """
        [i0]
        i2 = int_lt(i0, 10)
        guard_true(i2) []
        i3 = int_ge(i0, 0)
        guard_true(i3) []
        jump()
        """
        self.optimize_loop(ops, expected)
        #
        ops = """
        [i0]
        i2 = int_lt(i0, 10)
        guard_true(i2) []
        i3 = int_ge(i0, 0)
        guard_true(i3) []
        i4 = uint_ge(8, i0)
        guard_true(i4) []
        jump()
        """
        self.optimize_loop(ops, ops)

    @pytest.mark.xfail()  # see comment about optimize_UINT in intbounds.py
    def test_bound_unsigned_not_ge(self):
        ops = """
        [i0]
        i2 = int_lt(i0, 10)
        guard_true(i2) []
        i3 = int_ge(i0, 0)
        guard_true(i3) []
        i4 = uint_ge(i0, 10)
        guard_false(i4) []
        jump()
        """
        expected = """
        [i0]
        i2 = int_lt(i0, 10)
        guard_true(i2) []
        i3 = int_ge(i0, 0)
        guard_true(i3) []
        jump()
        """
        self.optimize_loop(ops, expected)

    @pytest.mark.xfail()  # see comment about optimize_UINT in intbounds.py
    def test_bound_unsigned_not_gt(self):
        ops = """
        [i0]
        i2 = int_lt(i0, 10)
        guard_true(i2) []
        i3 = int_ge(i0, 0)
        guard_true(i3) []
        i4 = uint_gt(i0, 9)
        guard_false(i4) []
        jump()
        """
        expected = """
        [i0]
        i2 = int_lt(i0, 10)
        guard_true(i2) []
        i3 = int_ge(i0, 0)
        guard_true(i3) []
        jump()
        """
        self.optimize_loop(ops, expected)

    @pytest.mark.xfail()  # see comment about optimize_UINT in intbounds.py
    def test_bound_unsigned_not_le(self):
        ops = """
        [i0]
        i2 = int_lt(i0, 10)
        guard_true(i2) []
        i3 = int_ge(i0, 0)
        guard_true(i3) []
        i4 = uint_le(10, i0)
        guard_false(i4) []
        jump()
        """
        expected = """
        [i0]
        i2 = int_lt(i0, 10)
        guard_true(i2) []
        i3 = int_ge(i0, 0)
        guard_true(i3) []
        jump()
        """
        self.optimize_loop(ops, expected)

    @pytest.mark.xfail()  # see comment about optimize_UINT in intbounds.py
    def test_bound_unsigned_not_lt(self):
        ops = """
        [i0]
        i2 = int_lt(i0, 10)
        guard_true(i2) []
        i3 = int_ge(i0, 0)
        guard_true(i3) []
        i4 = uint_lt(9, i0)
        guard_false(i4) []
        jump()
        """
        expected = """
        [i0]
        i2 = int_lt(i0, 10)
        guard_true(i2) []
        i3 = int_ge(i0, 0)
        guard_true(i3) []
        jump()
        """
        self.optimize_loop(ops, expected)
        #
        ops = """
        [i0]
        i2 = int_lt(i0, 10)
        guard_true(i2) []
        i3 = int_ge(i0, 0)
        guard_true(i3) []
        i4 = uint_lt(8, i0)
        guard_true(i4) []
        jump()
        """
        self.optimize_loop(ops, ops)

    @pytest.mark.xfail()  # see comment about optimize_UINT in intbounds.py
    def test_bound_unsigned_lt_inv(self):
        ops = """
        [i0]
        i1 = uint_lt(i0, 10)
        guard_true(i1) []
        i2 = int_lt(i0, 10)
        guard_true(i2) []
        i3 = int_ge(i0, 0)
        guard_true(i3) []
        jump()
        """
        expected = """
        [i0]
        i1 = uint_lt(i0, 10)
        guard_true(i1) []
        jump()
        """
        self.optimize_loop(ops, expected)

    @pytest.mark.xfail()  # see comment about optimize_UINT in intbounds.py
    def test_bound_unsigned_range(self):
        ops = """
        [i0]
        i2 = uint_lt(i0, -10)
        guard_true(i2) []
        i3 = uint_gt(i0, -20)
        guard_true(i3) []
        jump()
        """
        self.optimize_loop(ops, ops)

    @pytest.mark.xfail()  # see comment about optimize_UINT in intbounds.py
    def test_bound_unsigned_le_inv(self):
        ops = """
        [i0]
        i1 = uint_le(i0, 10)
        guard_true(i1) []
        i2 = int_lt(i0, 11)
        guard_true(i2) []
        i3 = int_ge(i0, 0)
        guard_true(i3) []
        jump()
        """
        expected = """
        [i0]
        i1 = uint_le(i0, 10)
        guard_true(i1) []
        jump()
        """
        self.optimize_loop(ops, expected)

    @pytest.mark.xfail()  # see comment about optimize_UINT in intbounds.py
    def test_bound_unsigned_gt_inv(self):
        ops = """
        [i0]
        i1 = uint_gt(10, i0)
        guard_true(i1) []
        i2 = int_lt(i0, 10)
        guard_true(i2) []
        i3 = int_ge(i0, 0)
        guard_true(i3) []
        jump()
        """
        expected = """
        [i0]
        i1 = uint_gt(10, i0)
        guard_true(i1) []
        jump()
        """
        self.optimize_loop(ops, expected)

    @pytest.mark.xfail()  # see comment about optimize_UINT in intbounds.py
    def test_bound_unsigned_ge_inv(self):
        ops = """
        [i0]
        i1 = uint_ge(10, i0)
        guard_true(i1) []
        i2 = int_lt(i0, 11)
        guard_true(i2) []
        i3 = int_ge(i0, 0)
        guard_true(i3) []
        jump()
        """
        expected = """
        [i0]
        i1 = uint_ge(10, i0)
        guard_true(i1) []
        jump()
        """
        self.optimize_loop(ops, expected)

    @pytest.mark.xfail()  # see comment about optimize_UINT in intbounds.py
    def test_bound_unsigned_bug1(self):
        ops = """
        [i0]
        i1 = int_ge(i0, 5)
        guard_true(i1) []
        i2 = uint_lt(i0, -50)
        guard_true(i2) []
        jump()
        """
        self.optimize_loop(ops, ops)

