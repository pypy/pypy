import pytest
from rpython.jit.metainterp.optimizeopt.test.test_optimizebasic import BaseTestBasic

class TestOptimizeHeap(BaseTestBasic):

    def test_duplicate_getfield_1(self):
        ops = """
        [p1, p2]
        i1 = getfield_gc_i(p1, descr=valuedescr)
        i2 = getfield_gc_i(p2, descr=valuedescr)
        i3 = getfield_gc_i(p1, descr=valuedescr)
        i4 = getfield_gc_i(p2, descr=valuedescr)
        jump(p1, p2, i1, i2, i3, i4)
        """
        expected = """
        [p1, p2]
        i1 = getfield_gc_i(p1, descr=valuedescr)
        i2 = getfield_gc_i(p2, descr=valuedescr)
        jump(p1, p2, i1, i2, i1, i2)
        """
        self.optimize_loop(ops, expected)

    def test_getfield_after_setfield(self):
        ops = """
        [p1, i1]
        setfield_gc(p1, i1, descr=valuedescr)
        i2 = getfield_gc_i(p1, descr=valuedescr)
        jump(p1, i1, i2)
        """
        expected = """
        [p1, i1]
        setfield_gc(p1, i1, descr=valuedescr)
        jump(p1, i1, i1)
        """
        self.optimize_loop(ops, expected)

    def test_setfield_of_different_type_does_not_clear(self):
        ops = """
        [p1, p2, i1]
        setfield_gc(p1, i1, descr=valuedescr)
        setfield_gc(p2, p1, descr=nextdescr)
        i2 = getfield_gc_i(p1, descr=valuedescr)
        jump(p1, p2, i1, i2)
        """
        expected = """
        [p1, p2, i1]
        setfield_gc(p1, i1, descr=valuedescr)
        setfield_gc(p2, p1, descr=nextdescr)
        jump(p1, p2, i1, i1)
        """
        self.optimize_loop(ops, expected)

    def test_setfield_of_same_type_clears(self):
        ops = """
        [p1, p2, i1, i2]
        setfield_gc(p1, i1, descr=valuedescr)
        setfield_gc(p2, i2, descr=valuedescr)
        i3 = getfield_gc_i(p1, descr=valuedescr)
        jump(p1, p2, i1, i3)
        """
        self.optimize_loop(ops, ops)

    def test_duplicate_getfield_mergepoint_has_no_side_effects(self):
        ops = """
        [p1]
        i1 = getfield_gc_i(p1, descr=valuedescr)
        debug_merge_point(15, 0, 1)
        i2 = getfield_gc_i(p1, descr=valuedescr)
        jump(p1, i1, i2)
        """
        expected = """
        [p1]
        i1 = getfield_gc_i(p1, descr=valuedescr)
        debug_merge_point(15, 0, 1)
        jump(p1, i1, i1)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_getfield_ovf_op_does_not_clear(self):
        ops = """
        [p1]
        i1 = getfield_gc_i(p1, descr=valuedescr)
        i2 = int_add_ovf(i1, 14)
        guard_no_overflow() []
        i3 = getfield_gc_i(p1, descr=valuedescr)
        jump(p1, i2, i3)
        """
        expected = """
        [p1]
        i1 = getfield_gc_i(p1, descr=valuedescr)
        i2 = int_add_ovf(i1, 14)
        guard_no_overflow() []
        jump(p1, i2, i1)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_getfield_setarrayitem_does_not_clear(self):
        ops = """
        [p1, p2]
        i1 = getfield_gc_i(p1, descr=valuedescr)
        setarrayitem_gc(p2, 0, p1, descr=arraydescr2)
        i3 = getfield_gc_i(p1, descr=valuedescr)
        jump(p1, p2, i1, i3)
        """
        expected = """
        [p1, p2]
        i1 = getfield_gc_i(p1, descr=valuedescr)
        setarrayitem_gc(p2, 0, p1, descr=arraydescr2)
        jump(p1, p2, i1, i1)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_getfield_constant(self):
        ops = """
        []
        i1 = getfield_gc_i(ConstPtr(myptr), descr=valuedescr)
        i2 = getfield_gc_i(ConstPtr(myptr), descr=valuedescr)
        jump(i1, i2)
        """
        expected = """
        []
        i1 = getfield_gc_i(ConstPtr(myptr), descr=valuedescr)
        jump(i1, i1)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_getfield_sideeffects_1(self):
        ops = """
        [p1]
        i1 = getfield_gc_i(p1, descr=valuedescr)
        escape_n()
        i2 = getfield_gc_i(p1, descr=valuedescr)
        jump(p1, i1, i2)
        """
        self.optimize_loop(ops, ops)

    def test_duplicate_getfield_sideeffects_2(self):
        ops = """
        [p1, i1]
        setfield_gc(p1, i1, descr=valuedescr)
        escape_n()
        i2 = getfield_gc_i(p1, descr=valuedescr)
        jump(p1, i1, i2)
        """
        self.optimize_loop(ops, ops)

    def test_duplicate_setfield_1(self):
        ops = """
        [p1, i1, i2]
        setfield_gc(p1, i1, descr=valuedescr)
        setfield_gc(p1, i2, descr=valuedescr)
        jump(p1, i1, i2)
        """
        expected = """
        [p1, i1, i2]
        setfield_gc(p1, i2, descr=valuedescr)
        jump(p1, i1, i2)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_setfield_2(self):
        ops = """
        [p1, i1, i3]
        setfield_gc(p1, i1, descr=valuedescr)
        i2 = getfield_gc_i(p1, descr=valuedescr)
        setfield_gc(p1, i3, descr=valuedescr)
        jump(p1, i1, i3, i2)
        """
        expected = """
        [p1, i1, i3]
        setfield_gc(p1, i3, descr=valuedescr)
        jump(p1, i1, i3, i1)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_setfield_3(self):
        ops = """
        [p1, p2, i1, i3]
        setfield_gc(p1, i1, descr=valuedescr)
        i2 = getfield_gc_i(p2, descr=valuedescr)
        setfield_gc(p1, i3, descr=valuedescr)
        jump(p1, p2, i1, i3, i2)
        """
        # potential aliasing of p1 and p2 means that we cannot kill the
        # the setfield_gc
        self.optimize_loop(ops, ops)

    def test_duplicate_setfield_4(self):
        ops = """
        [p1, i1, i2, p3]
        setfield_gc(p1, i1, descr=valuedescr)
        #
        # some operations on which the above setfield_gc cannot have effect
        i3 = getarrayitem_gc_i(p3, 1, descr=arraydescr)
        i4 = getarrayitem_gc_i(p3, i3, descr=arraydescr)
        i5 = int_add(i3, i4)
        setarrayitem_gc(p3, 0, i5, descr=arraydescr)
        setfield_gc(p1, i4, descr=nextdescr)
        #
        setfield_gc(p1, i2, descr=valuedescr)
        jump(p1, i1, i2, p3)
        """
        expected = """
        [p1, i1, i2, p3]
        #
        i3 = getarrayitem_gc_i(p3, 1, descr=arraydescr)
        i4 = getarrayitem_gc_i(p3, i3, descr=arraydescr)
        i5 = int_add(i3, i4)
        #
        setfield_gc(p1, i2, descr=valuedescr)
        setfield_gc(p1, i4, descr=nextdescr)
        setarrayitem_gc(p3, 0, i5, descr=arraydescr)
        jump(p1, i1, i2, p3)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_setfield_5(self):
        ops = """
        [p0, i1]
        p1 = new_with_vtable(descr=nodesize)
        setfield_gc(p1, i1, descr=valuedescr)
        setfield_gc(p0, p1, descr=nextdescr)
        setfield_raw(i1, i1, descr=valuedescr)    # random op with side-effects
        p2 = getfield_gc_r(p0, descr=nextdescr)
        i2 = getfield_gc_i(p2, descr=valuedescr)
        setfield_gc(p0, NULL, descr=nextdescr)
        jump(p0, i1, i2)
        """
        expected = """
        [p0, i1]
        setfield_raw(i1, i1, descr=valuedescr)
        setfield_gc(p0, NULL, descr=nextdescr)
        jump(p0, i1, i1)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_setfield_sideeffects_1(self):
        ops = """
        [p1, i1, i2]
        setfield_gc(p1, i1, descr=valuedescr)
        escape_n()
        setfield_gc(p1, i2, descr=valuedescr)
        jump(p1, i1, i2)
        """
        self.optimize_loop(ops, ops)

    def test_duplicate_setfield_residual_guard_1(self):
        ops = """
        [p1, i1, i2, i3]
        setfield_gc(p1, i1, descr=valuedescr)
        guard_true(i3) []
        i4 = int_neg(i2)
        setfield_gc(p1, i2, descr=valuedescr)
        jump(p1, i1, i2, i4)
        """
        self.optimize_loop(ops, ops)

    def test_duplicate_setfield_residual_guard_2(self):
        # the difference with the previous test is that the field value is
        # a virtual, which we try hard to keep virtual
        ops = """
        [p1, i2, i3]
        p2 = new_with_vtable(descr=nodesize)
        setfield_gc(p1, p2, descr=nextdescr)
        guard_true(i3) []
        i4 = int_neg(i2)
        setfield_gc(p1, NULL, descr=nextdescr)
        jump(p1, i2, i4)
        """
        expected = """
        [p1, i2, i3]
        guard_true(i3) [p1]
        i4 = int_neg(i2)
        setfield_gc(p1, NULL, descr=nextdescr)
        jump(p1, i2, i4)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_setfield_residual_guard_3(self):
        ops = """
        [p1, i2, i3]
        p2 = new_with_vtable(descr=nodesize)
        setfield_gc(p2, i2, descr=valuedescr)
        setfield_gc(p1, p2, descr=nextdescr)
        guard_true(i3) []
        i4 = int_neg(i2)
        setfield_gc(p1, NULL, descr=nextdescr)
        jump(p1, i2, i4)
        """
        expected = """
        [p1, i2, i3]
        guard_true(i3) [i2, p1]
        i4 = int_neg(i2)
        setfield_gc(p1, NULL, descr=nextdescr)
        jump(p1, i2, i4)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_setfield_residual_guard_4(self):
        # test that the setfield_gc does not end up between int_eq and
        # the following guard_true
        ops = """
        [p1, i1, i2, i3]
        setfield_gc(p1, i1, descr=valuedescr)
        i5 = int_eq(i3, 5)
        guard_true(i5) []
        i4 = int_neg(i2)
        setfield_gc(p1, i2, descr=valuedescr)
        jump(p1, i1, i2, i4)
        """
        self.optimize_loop(ops, ops)

    def test_setfield_int_eq_result(self):
        # test that the setfield_gc does not end up before int_eq
        ops = """
        [p1, i1, i2]
        i3 = int_eq(i1, i2)
        setfield_gc(p1, i3, descr=valuedescr)
        jump(p1, i1, i2)
        """
        self.optimize_loop(ops, ops)

    def test_duplicate_setfield_aliasing(self):
        # a case where aliasing issues (and not enough cleverness) mean
        # that we fail to remove any setfield_gc
        ops = """
        [p1, p2, i1, i2, i3]
        setfield_gc(p1, i1, descr=valuedescr)
        setfield_gc(p2, i2, descr=valuedescr)
        setfield_gc(p1, i3, descr=valuedescr)
        jump(p1, p2, i1, i2, i3)
        """
        self.optimize_loop(ops, ops)

    def test_duplicate_setfield_guard_value_const(self):
        ops = """
        [p1, i1, i2]
        guard_value(p1, ConstPtr(myptr)) []
        setfield_gc(p1, i1, descr=valuedescr)
        setfield_gc(ConstPtr(myptr), i2, descr=valuedescr)
        jump(p1, i1, i2)
        """
        expected = """
        [p1, i1, i2]
        guard_value(p1, ConstPtr(myptr)) []
        setfield_gc(ConstPtr(myptr), i2, descr=valuedescr)
        jump(ConstPtr(myptr), i1, i2)
        """
        self.optimize_loop(ops, expected)

    @pytest.mark.xfail
    def test_forced_virtuals_aliasing(self):
        ops = """
        [i0, i1]
        p0 = new(descr=ssize)
        p1 = new(descr=ssize)
        escape_n(p0)
        escape_n(p1)
        setfield_gc(p0, i0, descr=adescr)
        setfield_gc(p1, i1, descr=adescr)
        i2 = getfield_gc_i(p0, descr=adescr)
        jump(i2, i2)
        """
        expected = """
        [i0, i1]
        p0 = new(descr=ssize)
        escape_n(p0)
        p1 = new(descr=ssize)
        escape_n(p1)
        setfield_gc(p0, i0, descr=adescr)
        setfield_gc(p1, i1, descr=adescr)
        jump(i0, i0)
        """
        # setfields on things that used to be virtual still can't alias each
        # other
        self.optimize_loop(ops, expected)

    def test_setfield_aliasing_by_class(self):
        ops = """
        [p1, p2, p3, p4]
        guard_class(p1, ConstClass(node_vtable2)) []
        guard_class(p2, ConstClass(node_vtable)) []
        setfield_gc(p1, p3, descr=nextdescr)
        setfield_gc(p2, p4, descr=nextdescr)
        p5 = getfield_gc_i(p1, descr=nextdescr)
        jump(p1, p2, p5)
        """
        expected = """
        [p1, p2, p3, p4]
        guard_class(p1, ConstClass(node_vtable2)) []
        guard_class(p2, ConstClass(node_vtable)) []
        setfield_gc(p1, p3, descr=nextdescr)
        setfield_gc(p2, p4, descr=nextdescr)
        jump(p1, p2, p3)
        """
        self.optimize_loop(ops, expected)

    def test_setfield_aliasing_by_field_content(self):
        ops = """
        [p1, p2, p3, p4]
        i1 = getfield_gc_i(p1, descr=valuedescr)
        guard_value(i1, 1) []
        i2 = getfield_gc_i(p2, descr=valuedescr)
        guard_value(i2, 2) []
        setfield_gc(p1, p3, descr=nextdescr)
        setfield_gc(p2, p4, descr=nextdescr)
        p5 = getfield_gc_i(p1, descr=nextdescr)
        jump(p1, p2, p5)
        """
        expected = """
        [p1, p2, p3, p4]
        i1 = getfield_gc_i(p1, descr=valuedescr)
        guard_value(i1, 1) []
        i2 = getfield_gc_i(p2, descr=valuedescr)
        guard_value(i2, 2) []
        setfield_gc(p1, p3, descr=nextdescr)
        setfield_gc(p2, p4, descr=nextdescr)
        jump(p1, p2, p3)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_getarrayitem_1(self):
        ops = """
        [p1]
        p2 = getarrayitem_gc_r(p1, 0, descr=arraydescr2)
        p3 = getarrayitem_gc_r(p1, 1, descr=arraydescr2)
        p4 = getarrayitem_gc_r(p1, 0, descr=arraydescr2)
        p5 = getarrayitem_gc_r(p1, 1, descr=arraydescr2)
        jump(p1, p2, p3, p4, p5)
        """
        expected = """
        [p1]
        p2 = getarrayitem_gc_r(p1, 0, descr=arraydescr2)
        p3 = getarrayitem_gc_r(p1, 1, descr=arraydescr2)
        jump(p1, p2, p3, p2, p3)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_getarrayitem_after_setarrayitem_1(self):
        ops = """
        [p1, p2]
        setarrayitem_gc(p1, 0, p2, descr=arraydescr2)
        p3 = getarrayitem_gc_r(p1, 0, descr=arraydescr2)
        jump(p1, p3, p3)
        """
        expected = """
        [p1, p2]
        setarrayitem_gc(p1, 0, p2, descr=arraydescr2)
        jump(p1, p2, p2)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_getarrayitem_after_setarrayitem_3(self):
        ops = """
        [p1, p2, p3, p4, i1]
        setarrayitem_gc(p1, i1, p2, descr=arraydescr2)
        setarrayitem_gc(p1, 0, p3, descr=arraydescr2)
        setarrayitem_gc(p1, 1, p4, descr=arraydescr2)
        p5 = getarrayitem_gc_r(p1, i1, descr=arraydescr2)
        p6 = getarrayitem_gc_r(p1, 0, descr=arraydescr2)
        p7 = getarrayitem_gc_r(p1, 1, descr=arraydescr2)
        jump(p1, p2, p3, p4, i1, p5, p6, p7)
        """
        expected = """
        [p1, p2, p3, p4, i1]
        setarrayitem_gc(p1, i1, p2, descr=arraydescr2)
        setarrayitem_gc(p1, 0, p3, descr=arraydescr2)
        setarrayitem_gc(p1, 1, p4, descr=arraydescr2)
        p5 = getarrayitem_gc_r(p1, i1, descr=arraydescr2)
        jump(p1, p2, p3, p4, i1, p5, p3, p4)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_getarrayitem_after_setarrayitem_and_guard(self):
        ops = """
        [p0, p1, p2, p3, i1]
        p4 = getarrayitem_gc_r(p0, 0, descr=arraydescr2)
        p5 = getarrayitem_gc_r(p0, 1, descr=arraydescr2)
        p6 = getarrayitem_gc_r(p1, 0, descr=arraydescr2)
        setarrayitem_gc(p1, 1, p3, descr=arraydescr2)
        guard_true(i1) [i1]
        p7 = getarrayitem_gc_r(p0, 0, descr=arraydescr2)
        p8 = getarrayitem_gc_r(p0, 1, descr=arraydescr2)
        p9 = getarrayitem_gc_r(p1, 0, descr=arraydescr2)
        p10 = getarrayitem_gc_r(p1, 1, descr=arraydescr2)
        jump(p0, p1, p2, p3, i1, p4, p5, p6, p7, p8, p9, p10)
        """
        expected = """
        [p0, p1, p2, p3, i1]
        p4 = getarrayitem_gc_r(p0, 0, descr=arraydescr2)
        p5 = getarrayitem_gc_r(p0, 1, descr=arraydescr2)
        p6 = getarrayitem_gc_r(p1, 0, descr=arraydescr2)
        setarrayitem_gc(p1, 1, p3, descr=arraydescr2)
        guard_true(i1) [i1]
        p8 = getarrayitem_gc_r(p0, 1, descr=arraydescr2)
        jump(p0, p1, p2, p3, 1, p4, p5, p6, p4, p8, p6, p3)
        """
        self.optimize_loop(ops, expected)

    def test_getarrayitem_pure_does_not_invalidate(self):
        ops = """
        [p1, p2]
        p3 = getarrayitem_gc_r(p1, 0, descr=arraydescr2)
        i4 = getfield_gc_i(ConstPtr(myptr3), descr=valuedescr3)
        p5 = getarrayitem_gc_r(p1, 0, descr=arraydescr2)
        jump(p1, p2, p3, i4, p5)
        """
        expected = """
        [p1, p2]
        p3 = getarrayitem_gc_r(p1, 0, descr=arraydescr2)
        jump(p1, p2, p3, 7, p3)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_getarrayitem_after_setarrayitem_two_arrays(self):
        ops = """
        [p1, p2, p3, p4, i1]
        setarrayitem_gc(p1, 0, p3, descr=arraydescr2)
        setarrayitem_gc(p2, 1, p4, descr=arraydescr2)
        p5 = getarrayitem_gc_r(p1, 0, descr=arraydescr2)
        p6 = getarrayitem_gc_r(p2, 1, descr=arraydescr2)
        jump(p1, p2, p3, p4, i1, p5, p6)
        """
        expected = """
        [p1, p2, p3, p4, i1]
        setarrayitem_gc(p1, 0, p3, descr=arraydescr2)
        setarrayitem_gc(p2, 1, p4, descr=arraydescr2)
        jump(p1, p2, p3, p4, i1, p3, p4)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_getarrayitem_after_setarrayitem_bug(self):
        ops = """
        [p0, i0, i1]
        setarrayitem_gc(p0, 0, i0, descr=arraydescr)
        i6 = int_add(i0, 1)
        setarrayitem_gc(p0, i1, i6, descr=arraydescr)
        i10 = getarrayitem_gc_i(p0, 0, descr=arraydescr)
        i11 = int_add(i10, i0)
        jump(p0, i11, i1)
        """
        expected = """
        [p0, i0, i1]
        i6 = int_add(i0, 1)
        setarrayitem_gc(p0, 0, i0, descr=arraydescr)
        setarrayitem_gc(p0, i1, i6, descr=arraydescr)
        i10 = getarrayitem_gc_i(p0, 0, descr=arraydescr)
        i11 = int_add(i10, i0)
        jump(p0, i11, i1)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_getarrayitem_after_setarrayitem_bug2(self):
        ops = """
        [p0, i0, i1]
        i2 = getarrayitem_gc_i(p0, 0, descr=arraydescr)
        i6 = int_add(i0, 1)
        setarrayitem_gc(p0, i1, i6, descr=arraydescr)
        i10 = getarrayitem_gc_i(p0, 0, descr=arraydescr)
        i11 = int_add(i10, i2)
        jump(p0, i11, i1)
        """
        expected = """
        [p0, i0, i1]
        i2 = getarrayitem_gc_i(p0, 0, descr=arraydescr)
        i6 = int_add(i0, 1)
        setarrayitem_gc(p0, i1, i6, descr=arraydescr)
        i10 = getarrayitem_gc_i(p0, 0, descr=arraydescr)
        i11 = int_add(i10, i2)
        jump(p0, i11, i1)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_getarrayitem_varindex(self):
        ops = """
        [p1, i1]
        p2 = getarrayitem_gc_r(p1, i1, descr=arraydescr2)
        p4 = getarrayitem_gc_r(p1, i1, descr=arraydescr2)
        jump(p1, p2, p4)
        """
        expected = """
        [p1, i1]
        p2 = getarrayitem_gc_r(p1, i1, descr=arraydescr2)
        jump(p1, p2, p2)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_getarrayitem_varindex_two_arrays(self):
        ops = """
        [p1, p2, i1]
        p3 = getarrayitem_gc_r(p1, i1, descr=arraydescr2)
        p4 = getarrayitem_gc_r(p2, i1, descr=arraydescr2)
        p5 = getarrayitem_gc_r(p1, i1, descr=arraydescr2)
        p6 = getarrayitem_gc_r(p2, i1, descr=arraydescr2)
        jump(p3, p4, p5, p6)
        """
        expected = """
        [p1, p2, i1]
        p3 = getarrayitem_gc_r(p1, i1, descr=arraydescr2)
        p4 = getarrayitem_gc_r(p2, i1, descr=arraydescr2)
        jump(p3, p4, p3, p4)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_getarrayitem_invalidated_varindex(self):
        ops = """
        [p1, i1]
        p2 = getarrayitem_gc_r(p1, i1, descr=arraydescr2)
        setarrayitem_gc(p1, 1, 23, descr=arraydescr2)
        p4 = getarrayitem_gc_r(p1, i1, descr=arraydescr2)
        jump(p1, p2, p4)
        """
        expected = ops
        self.optimize_loop(ops, expected)

    def test_duplicate_getarrayitem_after_setarrayitem_2(self):
        ops = """
        [p1, p2, p3, i1]
        setarrayitem_gc(p1, 0, p2, descr=arraydescr2)
        setarrayitem_gc(p1, i1, p3, descr=arraydescr2)
        p4 = getarrayitem_gc_i(p1, 0, descr=arraydescr2)
        p5 = getarrayitem_gc_i(p1, i1, descr=arraydescr2)
        jump(p1, p2, p3, i1, p4, p5)
        """
        expected = """
        [p1, p2, p3, i1]
        setarrayitem_gc(p1, 0, p2, descr=arraydescr2)
        setarrayitem_gc(p1, i1, p3, descr=arraydescr2)
        p4 = getarrayitem_gc_i(p1, 0, descr=arraydescr2)
        jump(p1, p2, p3, i1, p4, p3)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_getarrayitem_after_setarrayitem_varindex_two_arrays(self):
        ops = """
        [p1, p2, p3, p4, i1]
        setarrayitem_gc(p1, i1, p3, descr=arraydescr2)
        setarrayitem_gc(p2, i1, p4, descr=arraydescr2)
        p5 = getarrayitem_gc_r(p1, i1, descr=arraydescr2)
        p6 = getarrayitem_gc_r(p2, i1, descr=arraydescr2)
        jump(p3, p4, p5, p6)
        """
        expected = """
        [p1, p2, p3, p4, i1]
        setarrayitem_gc(p1, i1, p3, descr=arraydescr2)
        setarrayitem_gc(p2, i1, p4, descr=arraydescr2)
        p5 = getarrayitem_gc_r(p1, i1, descr=arraydescr2)
        jump(p3, p4, p5, p4)
        """
        self.optimize_loop(ops, expected)

    def test_duplicate_getarrayitem_after_setarrayitem_two_arrays_aliasing_via_length(self):
        ops = """
        [p1, p2, p3, p4]
        i2 = arraylen_gc(p1, descr=arraydescr2)
        guard_value(i2, 10) []
        i3 = arraylen_gc(p2, descr=arraydescr2)
        guard_value(i3, 15) []
        setarrayitem_gc(p1, 0, p3, descr=arraydescr2)
        setarrayitem_gc(p2, 0, p4, descr=arraydescr2)
        p5 = getarrayitem_gc_r(p1, 0, descr=arraydescr2)
        p6 = getarrayitem_gc_r(p2, 0, descr=arraydescr2)
        jump(p3, p4, p5, p6)
        """
        expected = """
        [p1, p2, p3, p4]
        i2 = arraylen_gc(p1, descr=arraydescr2)
        guard_value(i2, 10) []
        i3 = arraylen_gc(p2, descr=arraydescr2)
        guard_value(i3, 15) []
        setarrayitem_gc(p1, 0, p3, descr=arraydescr2)
        setarrayitem_gc(p2, 0, p4, descr=arraydescr2)
        jump(p3, p4, p3, p4)
        """
        self.optimize_loop(ops, expected)

    @pytest.mark.xfail()
    def test_duplicate_getarrayitem_after_setarrayitem_varindex_two_arrays_aliasing_via_length(self):
        ops = """
        [p1, p2, p3, p4, i1]
        i2 = arraylen_gc(p1, descr=arraydescr2)
        guard_value(i2, 10) []
        i3 = arraylen_gc(p2, descr=arraydescr2)
        guard_value(i3, 15) []
        setarrayitem_gc(p1, i1, p3, descr=arraydescr2)
        setarrayitem_gc(p2, i1, p4, descr=arraydescr2)
        p5 = getarrayitem_gc_r(p1, i1, descr=arraydescr2)
        p6 = getarrayitem_gc_r(p2, i1, descr=arraydescr2)
        jump(p3, p4, p5, p6)
        """
        expected = """
        [p1, p2, p3, p4, i1]
        i2 = arraylen_gc(p1, descr=arraydescr2)
        guard_value(i2, 10) []
        i3 = arraylen_gc(p2, descr=arraydescr2)
        guard_value(i3, 15) []
        setarrayitem_gc(p1, i1, p3, descr=arraydescr2)
        setarrayitem_gc(p2, i1, p4, descr=arraydescr2)
        jump(p3, p4, p3, p4)
        """
        self.optimize_loop(ops, expected)

    def test_ptr_eq_via_length(self):
        ops = """
        [p1, p2, p3, p4]
        i2 = arraylen_gc(p1, descr=arraydescr2)
        guard_value(i2, 10) []
        i3 = arraylen_gc(p2, descr=arraydescr2)
        guard_value(i3, 15) []
        i1 = ptr_eq(p1, p2)
        jump(i1)
        """
        expected = """
        [p1, p2, p3, p4]
        i2 = arraylen_gc(p1, descr=arraydescr2)
        guard_value(i2, 10) []
        i3 = arraylen_gc(p2, descr=arraydescr2)
        guard_value(i3, 15) []
        jump(0)
        """
        self.optimize_loop(ops, expected)
