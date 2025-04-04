import pytest
from rpython.jit.metainterp.optimizeopt.test.test_optimizebasic import BaseTestBasic

class TestOptimizeHeap(BaseTestBasic):

    def test_ooisnull_oononnull_2(self):
        ops = """
        [p0]
        guard_nonnull(p0) []
        guard_nonnull(p0) []
        jump(p0)
        """
        expected = """
        [p0]
        guard_nonnull(p0) []
        jump(p0)
        """
        self.optimize_loop(ops, expected)

    def test_ooisnull_on_null_ptr_1(self):
        ops = """
        [p0]
        guard_isnull(p0) []
        guard_isnull(p0) []
        jump(p0)
        """
        expected = """
        [p0]
        guard_isnull(p0) []
        jump(NULL)
        """
        self.optimize_loop(ops, expected)

    def test_ooisnull_oononnull_via_virtual(self):
        ops = """
        [p0]
        pv = new_with_vtable(descr=nodesize)
        setfield_gc(pv, p0, descr=valuedescr)
        guard_nonnull(p0) []
        p1 = getfield_gc_r(pv, descr=valuedescr)
        guard_nonnull(p1) []
        jump(p0)
        """
        expected = """
        [p0]
        guard_nonnull(p0) []
        jump(p0)
        """
        self.optimize_loop(ops, expected)

    def test_virtual_oois(self):
        ops = """
        [p0, p1, p2]
        guard_nonnull(p0) []
        i3 = ptr_ne(p0, NULL)
        guard_true(i3) []
        i4 = ptr_eq(p0, NULL)
        guard_false(i4) []
        i5 = ptr_ne(NULL, p0)
        guard_true(i5) []
        i6 = ptr_eq(NULL, p0)
        guard_false(i6) []
        i7 = ptr_ne(p0, p1)
        guard_true(i7) []
        i8 = ptr_eq(p0, p1)
        guard_false(i8) []
        i9 = ptr_ne(p0, p2)
        guard_true(i9) []
        i10 = ptr_eq(p0, p2)
        guard_false(i10) []
        i11 = ptr_ne(p2, p1)
        guard_true(i11) []
        i12 = ptr_eq(p2, p1)
        guard_false(i12) []
        jump(p0, p1, p2)
        """
        expected2 = """
        [p0, p1, p2]
        guard_nonnull(p0) []
        i7 = ptr_ne(p0, p1)
        guard_true(i7) []
        i9 = ptr_ne(p0, p2)
        guard_true(i9) []
        i11 = ptr_ne(p2, p1)
        guard_true(i11) []
        jump(p0, p1, p2)
        """
        self.optimize_loop(ops, expected2)

    def test_instance_ptr_eq_is_symmetric(self):
        ops = """
        [p0, p1]
        i0 = instance_ptr_eq(p0, p1)
        guard_false(i0) []
        i1 = instance_ptr_eq(p1, p0)
        guard_false(i1) []
        jump(p0, p1)
        """
        expected = """
        [p0, p1]
        i0 = instance_ptr_eq(p0, p1)
        guard_false(i0) []
        jump(p0, p1)
        """
        self.optimize_loop(ops, expected)

        ops = """
        [p0, p1]
        i0 = instance_ptr_ne(p0, p1)
        guard_true(i0) []
        i1 = instance_ptr_ne(p1, p0)
        guard_true(i1) []
        jump(p0, p1)
        """
        expected = """
        [p0, p1]
        i0 = instance_ptr_ne(p0, p1)
        guard_true(i0) []
        jump(p0, p1)
        """
        self.optimize_loop(ops, expected)

    def test_nonnull_from_setfield(self):
        ops = """
        [p0]
        setfield_gc(p0, 5, descr=valuedescr)     # forces p0 != NULL
        i0 = ptr_ne(p0, NULL)
        guard_true(i0) []
        i1 = ptr_eq(p0, NULL)
        guard_false(i1) []
        i2 = ptr_ne(NULL, p0)
        guard_true(i0) []
        i3 = ptr_eq(NULL, p0)
        guard_false(i1) []
        guard_nonnull(p0) []
        jump(p0)
        """
        expected = """
        [p0]
        setfield_gc(p0, 5, descr=valuedescr)
        jump(p0)
        """
        self.optimize_loop(ops, expected)

    def test_remove_guard_value_if_constant(self):
        ops = """
        [p1]
        guard_value(p1, ConstPtr(myptr)) []
        guard_value(p1, ConstPtr(myptr)) []
        jump(p1)
        """
        expected = """
        [p1]
        guard_value(p1, ConstPtr(myptr)) []
        jump(ConstPtr(myptr))
        """
        self.optimize_loop(ops, expected)

    def test_ooisnull_oononnull_1(self):
        ops = """
        [p0]
        guard_class(p0, ConstClass(node_vtable)) []
        guard_nonnull(p0) []
        jump(p0)
        """
        expected = """
        [p0]
        guard_class(p0, ConstClass(node_vtable)) []
        jump(p0)
        """
        self.optimize_loop(ops, expected)

    def test_oois_1(self):
        ops = """
        [p0]
        guard_class(p0, ConstClass(node_vtable)) []
        i0 = instance_ptr_ne(p0, NULL)
        guard_true(i0) []
        i1 = instance_ptr_eq(p0, NULL)
        guard_false(i1) []
        i2 = instance_ptr_ne(NULL, p0)
        guard_true(i0) []
        i3 = instance_ptr_eq(NULL, p0)
        guard_false(i1) []
        jump(p0)
        """
        expected = """
        [p0]
        guard_class(p0, ConstClass(node_vtable)) []
        jump(p0)
        """
        self.optimize_loop(ops, expected)

    def test_guard_class_oois(self):
        ops = """
        [p1]
        guard_class(p1, ConstClass(node_vtable2)) []
        i = instance_ptr_ne(ConstPtr(myptr), p1)
        guard_true(i) []
        jump(p1)
        """
        expected = """
        [p1]
        guard_class(p1, ConstClass(node_vtable2)) []
        jump(p1)
        """
        self.optimize_loop(ops, expected)

    def test_oois_of_itself(self):
        ops = """
        [p0]
        p1 = getfield_gc_r(p0, descr=nextdescr)
        p2 = getfield_gc_r(p0, descr=nextdescr)
        i1 = ptr_eq(p1, p2)
        guard_true(i1) []
        i2 = ptr_ne(p1, p2)
        guard_false(i2) []
        jump(p0)
        """
        expected = """
        [p0]
        p1 = getfield_gc_r(p0, descr=nextdescr)
        jump(p0)
        """
        self.optimize_loop(ops, expected)


    def test_remove_guard_class_1(self):
        ops = """
        [p0]
        guard_class(p0, ConstClass(node_vtable)) []
        guard_class(p0, ConstClass(node_vtable)) []
        jump(p0)
        """
        expected = """
        [p0]
        guard_class(p0, ConstClass(node_vtable)) []
        jump(p0)
        """
        self.optimize_loop(ops, expected)

    def test_remove_guard_class_2(self):
        ops = """
        [i0]
        p0 = new_with_vtable(descr=nodesize)
        escape_n(p0)
        guard_class(p0, ConstClass(node_vtable)) []
        jump(i0)
        """
        expected = """
        [i0]
        p0 = new_with_vtable(descr=nodesize)
        escape_n(p0)
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_remove_guard_class_constant(self):
        ops = """
        [i0]
        p0 = same_as_r(ConstPtr(myptr))
        guard_class(p0, ConstClass(node_vtable)) []
        jump(i0)
        """
        expected = """
        [i0]
        jump(i0)
        """
        self.optimize_loop(ops, expected)

    def test_p123_simple(self):
        ops = """
        [i1, p2, p3]
        i3 = getfield_gc_i(p3, descr=valuedescr)
        escape_n(i3)
        p1 = new_with_vtable(descr=nodesize)
        setfield_gc(p1, i1, descr=valuedescr)
        jump(i1, p1, p2)
        """
        # We cannot track virtuals that survive for more than two iterations.
        self.optimize_loop(ops, ops)

    def test_p123_nested(self):
        ops = """
        [i1, p2, p3]
        i3 = getfield_gc_i(p3, descr=valuedescr)
        escape_n(i3)
        p1 = new_with_vtable(descr=nodesize)
        p1sub = new_with_vtable(descr=nodesize2)
        setfield_gc(p1, i1, descr=valuedescr)
        setfield_gc(p1sub, i1, descr=valuedescr)
        setfield_gc(p1, p1sub, descr=nextdescr)
        jump(i1, p1, p2)
        """
        expected = """
        [i1, p2, p3]
        i3 = getfield_gc_i(p3, descr=valuedescr)
        escape_n(i3)
        p1 = new_with_vtable(descr=nodesize)
        p1sub = new_with_vtable(descr=nodesize2)
        setfield_gc(p1sub, i1, descr=valuedescr)
        setfield_gc(p1, i1, descr=valuedescr)
        setfield_gc(p1, p1sub, descr=nextdescr)
        jump(i1, p1, p2)
        """
        # The same as test_p123_simple, but with a virtual containing another
        # virtual.
        self.optimize_loop(ops, expected)

    def test_p123_anti_nested(self):
        ops = """
        [i1, p2, p3]
        p3sub = getfield_gc_r(p3, descr=nextdescr)
        i3 = getfield_gc_i(p3sub, descr=valuedescr)
        escape_n(i3)
        p2sub = new_with_vtable(descr=nodesize2)
        setfield_gc(p2sub, i1, descr=valuedescr)
        setfield_gc(p2, p2sub, descr=nextdescr)
        p1 = new_with_vtable(descr=nodesize)
        jump(i1, p1, p2)
        """
        # The same as test_p123_simple, but in the end the "old" p2 contains
        # a "young" virtual p2sub.  Make sure it is all forced.
        self.optimize_loop(ops, ops)

    def test_constptr_guard_value(self):
        ops = """
        [p1]
        guard_value(p1, ConstPtr(myptr)) []
        jump(p1)
        """
        expected = """
        [p1]
        guard_value(p1, ConstPtr(myptr)) []
        jump(ConstPtr(myptr))
        """
        self.optimize_loop(ops, expected)

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
        [p0, i1, p3, i5, p4]
        p1 = new_with_vtable(descr=nodesize)
        setfield_gc(p1, i1, descr=valuedescr)
        setfield_gc(p0, p1, descr=nextdescr)
        setarrayitem_gc(p3, 0, i5, descr=arraydescr) # random op with side-effects
        p2 = getfield_gc_r(p0, descr=nextdescr)
        i2 = getfield_gc_i(p2, descr=valuedescr)
        setfield_gc(p0, p4, descr=nextdescr)
        jump(p0, i1, i2)
        """
        expected = """
        [p0, i1, p3, i5, p4]
        setfield_gc(p0, p4, descr=nextdescr)
        setarrayitem_gc(p3, 0, i5, descr=arraydescr) # random op with side-effects
        jump(p0, i1, i1)
        """
        self.optimize_loop(ops, expected)

    def test_virtual_struct_with_constptr_write(self):
        ops = """
        [p0, i1, p3, i5, p4]
        p1 = new_with_vtable(descr=nodesize)
        setfield_gc(p1, i1, descr=valuedescr)
        setfield_gc(p0, p1, descr=nextdescr)
        setfield_gc(ConstPtr(myptr), 23, descr=valuedescr) # random op with side-effects
        p2 = getfield_gc_r(p0, descr=nextdescr)
        i2 = getfield_gc_i(p2, descr=valuedescr)
        setfield_gc(p0, p4, descr=nextdescr)
        jump(p0, i1, i2)
        """
        expected = """
        [p0, i1, p3, i5, p4]
        setfield_gc(ConstPtr(myptr), 23, descr=valuedescr) # random op with side-effects
        setfield_gc(p0, p4, descr=nextdescr)
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

    def test_setfield_aliasing_by_field_content_bug(self):
        ops = """
        [p2, p3, p4]
        i1 = getfield_gc_i(ConstPtr(myptr), descr=valuedescr)
        guard_value(i1, 1) []
        i2 = getfield_gc_i(p2, descr=valuedescr)
        guard_value(i2, 2) []
        setfield_gc(ConstPtr(myptr), p3, descr=nextdescr)
        setfield_gc(p2, p4, descr=nextdescr)
        p5 = getfield_gc_i(ConstPtr(myptr), descr=nextdescr)
        jump(p2, p5)
        """
        # could do better, but at least we shouldn't crash
        self.optimize_loop(ops, ops)

    def test_getarrayitem_bounds(self):
        ops = """
        [p1]
        i1 = getarrayitem_gc_i(p1, 0, descr=int16arraydescr)
        i2 = int_gt(i1, 100000)
        jump(i2)
        """
        expected = """
        [p1]
        i1 = getarrayitem_gc_i(p1, 0, descr=int16arraydescr)
        jump(0)
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

    def test_sideeffect_pure_does_not_invalidate(self):
        ops = """
        [p1, p2]
        i4 = getfield_gc_i(p1, descr=valuedescr3)
        escape_n()
        i5 = getfield_gc_i(p1, descr=valuedescr3)
        jump(i4, i5)
        """
        expected = """
        [p1, p2]
        i4 = getfield_gc_i(p1, descr=valuedescr3)
        escape_n()
        jump(i4, i4)
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

    def test_arraylen_of_constant(self):
        ops = """
        []
        i2 = arraylen_gc(ConstPtr(myarray), descr=arraydescr)
        jump(i2)
        """
        expected = """
        []
        jump(13)
        """
        self.optimize_loop(ops, expected)


    def test_remove_duplicate_pure_op_with_descr(self):
        ops = """
        [p1]
        i0 = arraylen_gc(p1, descr=arraydescr)
        i1 = int_gt(i0, 0)
        guard_true(i1) []
        i2 = arraylen_gc(p1, descr=arraydescr)
        i3 = int_gt(i0, 0)
        guard_true(i3) []
        jump(p1)
        """
        expected = """
        [p1]
        i0 = arraylen_gc(p1, descr=arraydescr)
        i1 = int_gt(i0, 0)
        guard_true(i1) []
        jump(p1)
        """
        self.optimize_loop(ops, expected)

    # ____________________________________________________________
    # arraycopy tests

    def test_arraycopy_1(self):
        ops = '''
        [i0]
        p1 = new_array(3, descr=arraydescr)
        setarrayitem_gc(p1, 1, 1, descr=arraydescr)
        p2 = new_array(3, descr=arraydescr)
        setarrayitem_gc(p2, 1, 3, descr=arraydescr)
        call_n(0, p1, p2, 1, 1, 2, descr=arraycopydescr)
        i2 = getarrayitem_gc_i(p2, 1, descr=arraydescr)
        jump(i2)
        '''
        expected = '''
        [i0]
        jump(1)
        '''
        self.optimize_loop(ops, expected)

    def test_arraycopy_2(self):
        ops = '''
        [i0]
        p1 = new_array(3, descr=arraydescr)
        p2 = new_array(3, descr=arraydescr)
        setarrayitem_gc(p1, 0, i0, descr=arraydescr)
        setarrayitem_gc(p2, 0, 3, descr=arraydescr)
        call_n(0, p1, p2, 1, 1, 2, descr=arraycopydescr)
        i2 = getarrayitem_gc_i(p2, 0, descr=arraydescr)
        jump(i2)
        '''
        expected = '''
        [i0]
        jump(3)
        '''
        self.optimize_loop(ops, expected)

    def test_arraycopy_not_virtual(self):
        ops = '''
        [p0]
        p1 = new_array(3, descr=arraydescr)
        p2 = new_array(3, descr=arraydescr)
        setarrayitem_gc(p1, 2, 10, descr=arraydescr)
        setarrayitem_gc(p2, 2, 13, descr=arraydescr)
        call_n(0, p1, p2, 0, 0, 3, descr=arraycopydescr)
        jump(p2)
        '''
        expected = '''
        [p0]
        p2 = new_array(3, descr=arraydescr)
        setarrayitem_gc(p2, 2, 10, descr=arraydescr)
        jump(p2)
        '''
        self.optimize_loop(ops, expected)

    def test_arraycopy_not_virtual_2(self):
        ops = '''
        [p0]
        p1 = new_array(3, descr=arraydescr)
        call_n(0, p0, p1, 0, 0, 3, descr=arraycopydescr)
        i0 = getarrayitem_gc_i(p1, 0, descr=arraydescr)
        jump(i0)
        '''
        expected = '''
        [p0]
        i0 = getarrayitem_gc_i(p0, 0, descr=arraydescr)
        i1 = getarrayitem_gc_i(p0, 1, descr=arraydescr) # removed by the backend
        i2 = getarrayitem_gc_i(p0, 2, descr=arraydescr) # removed by the backend
        jump(i0)
        '''
        self.optimize_loop(ops, expected)

    def test_arraycopy_not_virtual_3(self):
        ops = '''
        [p0, p1]
        call_n(0, p0, p1, 0, 0, 3, descr=arraycopydescr)
        i0 = getarrayitem_gc_i(p1, 0, descr=arraydescr)
        jump(i0)
        '''
        expected = '''
        [p0, p1]
        i0 = getarrayitem_gc_i(p0, 0, descr=arraydescr)
        i1 = getarrayitem_gc_i(p0, 1, descr=arraydescr)
        i2 = getarrayitem_gc_i(p0, 2, descr=arraydescr)
        setarrayitem_gc(p1, 0, i0, descr=arraydescr)
        setarrayitem_gc(p1, 1, i1, descr=arraydescr)
        setarrayitem_gc(p1, 2, i2, descr=arraydescr)
        jump(i0)
        '''
        self.optimize_loop(ops, expected)

    def test_arraycopy_no_elem(self):
        """ this was actually observed in the wild
        """
        ops = '''
        [p1]
        p0 = new_array(0, descr=arraydescr)
        call_n(0, p0, p1, 0, 0, 0, descr=arraycopydescr)
        jump(p1)
        '''
        expected = '''
        [p1]
        jump(p1)
        '''
        self.optimize_loop(ops, expected)

    def test_arraycopy_invalidate_1(self):
        ops = """
        [i5, p0]
        p1 = new_array_clear(i5, descr=arraydescr)
        call_n(0, p0, p1, 0, 0, i5, descr=arraycopydescr)
        i2 = getarrayitem_gc_i(p1, 0, descr=arraydescr)   # != NULL
        jump(i2)
        """
        self.optimize_loop(ops, ops)

    def test_arraycopy_invalidate_2(self):
        ops = """
        [i5, p0]
        p1 = new_array_clear(i5, descr=arraydescr)
        call_n(0, p0, p1, 0, 0, 100, descr=arraycopydescr)
        i2 = getarrayitem_gc_i(p1, 0, descr=arraydescr)   # != NULL
        jump(i2)
        """
        self.optimize_loop(ops, ops)

    def test_arraycopy_invalidate_3(self):
        ops = """
        [i5, p0]
        p1 = new_array_clear(100, descr=arraydescr)
        call_n(0, p0, p1, 0, 0, i5, descr=arraycopydescr)
        i2 = getarrayitem_gc_i(p1, 0, descr=arraydescr)   # != NULL
        jump(i2)
        """
        self.optimize_loop(ops, ops)

    def test_arraycopy_invalidate_4(self):
        ops = """
        [i5, p0]
        p1 = new_array_clear(100, descr=arraydescr)
        call_n(0, p0, p1, 0, 0, 100, descr=arraycopydescr)
        i2 = getarrayitem_gc_i(p1, 0, descr=arraydescr)   # != NULL
        jump(i2)
        """
        self.optimize_loop(ops, ops)

    def test_arraymove_1(self):
        ops = '''
        [i0]
        p1 = new_array(6, descr=arraydescr)
        setarrayitem_gc(p1, 1, i0, descr=arraydescr)
        call_n(0, p1, 0, 2, 0, descr=arraymovedescr)    # 0-length arraymove
        i2 = getarrayitem_gc_i(p1, 1, descr=arraydescr)
        jump(i2)
        '''
        expected = '''
        [i0]
        jump(i0)
        '''
        self.optimize_loop(ops, expected)

    def test_framestackdepth_overhead(self):
        ops = """
        [p0, i22]
        i1 = getfield_gc_i(p0, descr=valuedescr)
        i2 = int_gt(i1, i22)
        guard_false(i2) []
        i3 = int_add(i1, 1)
        setfield_gc(p0, i3, descr=valuedescr)
        i4 = int_sub(i3, 1)
        setfield_gc(p0, i4, descr=valuedescr)
        i5 = int_gt(i4, i22)
        guard_false(i5) []
        i6 = int_add(i4, 1)
        p331 = force_token()
        i7 = int_sub(i6, 1)
        setfield_gc(p0, i7, descr=valuedescr)
        jump(p0, i22)
        """
        expected = """
        [p0, i22]
        i1 = getfield_gc_i(p0, descr=valuedescr)
        i2 = int_gt(i1, i22)
        guard_false(i2) []
        i3 = int_add(i1, 1)
        p331 = force_token()
        jump(p0, i22)
        """
        self.optimize_loop(ops, expected)
    # ____________________________________________________________
    # virtuals

    def test_virtual_3(self):
        ops = """
        [i]
        p1 = new_with_vtable(descr=nodesize)
        setfield_gc(p1, i, descr=valuedescr)
        i0 = getfield_gc_i(p1, descr=valuedescr)
        i1 = int_add(i0, 1)
        jump(i1)
        """
        expected = """
        [i]
        i1 = int_add(i, 1)
        jump(i1)
        """
        self.optimize_loop(ops, expected)

    def test_virtual_constant_isnull(self):
        ops = """
        [i0]
        p0 = new_with_vtable(descr=nodesize)
        setfield_gc(p0, NULL, descr=nextdescr)
        p2 = getfield_gc_r(p0, descr=nextdescr)
        i1 = ptr_eq(p2, NULL)
        jump(i1)
        """
        expected = """
        [i0]
        jump(1)
        """
        self.optimize_loop(ops, expected)

    def test_virtual_constant_isnonnull(self):
        ops = """
        [i0]
        p0 = new_with_vtable(descr=nodesize)
        setfield_gc(p0, ConstPtr(myptr), descr=nextdescr)
        p2 = getfield_gc_r(p0, descr=nextdescr)
        i1 = ptr_eq(p2, NULL)
        jump(i1)
        """
        expected = """
        [i0]
        jump(0)
        """
        self.optimize_loop(ops, expected)

    def test_virtual_uninit_read(self):
        ops = """
        [i0]
        p0 = new_with_vtable(descr=nodesize)
        i1 = getfield_gc_i(p0, descr=valuedescr)
        jump(i1)
        """
        expected = """
        [i0]
        jump(0)
        """
        self.optimize_loop(ops, expected)

    def test_nonvirtual_1(self):
        ops = """
        [i]
        p1 = new_with_vtable(descr=nodesize)
        setfield_gc(p1, i, descr=valuedescr)
        i0 = getfield_gc_i(p1, descr=valuedescr)
        i1 = int_add(i0, 1)
        jump(i1, p1)
        """
        expected = """
        [i]
        i1 = int_add(i, 1)
        p1 = new_with_vtable(descr=nodesize)
        setfield_gc(p1, i, descr=valuedescr)
        jump(i1, p1)
        """
        self.optimize_loop(ops, expected)

    def test_nonvirtual_2(self):
        ops = """
        [i, p0]
        i0 = getfield_gc_i(p0, descr=valuedescr)
        escape_n(p0)
        i1 = int_add(i0, i)
        p1 = new_with_vtable(descr=nodesize)
        setfield_gc(p1, i1, descr=valuedescr)
        jump(i, p1)
        """
        expected = ops
        self.optimize_loop(ops, expected)

    def test_nonvirtual_later(self):
        ops = """
        [i]
        p1 = new_with_vtable(descr=nodesize)
        setfield_gc(p1, i, descr=valuedescr)
        i1 = getfield_gc_i(p1, descr=valuedescr)
        escape_n(p1)
        i2 = getfield_gc_i(p1, descr=valuedescr)
        i3 = int_add(i1, i2)
        jump(i3)
        """
        expected = """
        [i]
        p1 = new_with_vtable(descr=nodesize)
        setfield_gc(p1, i, descr=valuedescr)
        escape_n(p1)
        i2 = getfield_gc_i(p1, descr=valuedescr)
        i3 = int_add(i, i2)
        jump(i3)
        """
        self.optimize_loop(ops, expected)

    def test_nonvirtual_write_null_fields_on_force(self):
        ops = """
        [i]
        p1 = new_with_vtable(descr=nodesize)
        setfield_gc(p1, i, descr=valuedescr)
        i1 = getfield_gc_i(p1, descr=valuedescr)
        setfield_gc(p1, 0, descr=valuedescr)
        escape_n(p1)
        i2 = getfield_gc_i(p1, descr=valuedescr)
        jump(i2)
        """
        expected = """
        [i]
        p1 = new_with_vtable(descr=nodesize)
        setfield_gc(p1, 0, descr=valuedescr)
        escape_n(p1)
        i2 = getfield_gc_i(p1, descr=valuedescr)
        jump(i2)
        """
        self.optimize_loop(ops, expected)

    def test_getfield_gc_1(self):
        ops = """
        [i]
        p1 = new_with_vtable(descr=nodesize3)
        setfield_gc(p1, i, descr=valuedescr3)
        i1 = getfield_gc_i(p1, descr=valuedescr3)
        jump(i1)
        """
        expected = """
        [i]
        jump(i)
        """
        self.optimize_loop(ops, expected)

    def test_getfield_gc_2(self):
        ops = """
        [i]
        i1 = getfield_gc_i(ConstPtr(myptr3), descr=valuedescr3)
        jump(i1)
        """
        expected = """
        [i]
        jump(7)
        """
        self.optimize_loop(ops, expected)

    def test_getfield_gc_nonpure_2(self):
        ops = """
        [i]
        i1 = getfield_gc_i(ConstPtr(myptr), descr=valuedescr)
        jump(i1)
        """
        expected = ops
        self.optimize_loop(ops, expected)

    def test_varray_1(self):
        ops = """
        [i1]
        p1 = new_array(3, descr=arraydescr)
        i3 = arraylen_gc(p1, descr=arraydescr)
        guard_value(i3, 3) []
        setarrayitem_gc(p1, 1, i1, descr=arraydescr)
        setarrayitem_gc(p1, 0, 25, descr=arraydescr)
        i2 = getarrayitem_gc_i(p1, 1, descr=arraydescr)
        jump(i2)
        """
        expected = """
        [i1]
        jump(i1)
        """
        self.optimize_loop(ops, expected)

    def test_varray_alloc_and_set(self):
        ops = """
        [i1]
        p1 = new_array(2, descr=arraydescr)
        setarrayitem_gc(p1, 0, 25, descr=arraydescr)
        i2 = getarrayitem_gc_i(p1, 0, descr=arraydescr)
        jump(i2)
        """
        expected = """
        [i1]
        jump(25)
        """
        self.optimize_loop(ops, expected)

    def test_varray_float(self):
        ops = """
        [f1]
        p1 = new_array(3, descr=floatarraydescr)
        i3 = arraylen_gc(p1, descr=floatarraydescr)
        guard_value(i3, 3) []
        setarrayitem_gc(p1, 1, f1, descr=floatarraydescr)
        setarrayitem_gc(p1, 0, 3.5, descr=floatarraydescr)
        f2 = getarrayitem_gc_f(p1, 1, descr=floatarraydescr)
        jump(f2)
        """
        expected = """
        [f1]
        jump(f1)
        """
        self.optimize_loop(ops, expected)

    def test_array_non_optimized_length(self):
        ops = """
        [i1]
        p1 = new_array(i1, descr=arraydescr)
        i2 = arraylen_gc(p1, descr=arraydescr)
        jump(i2)
        """
        expected = """
        [i1]
        p1 = new_array(i1, descr=arraydescr)
        jump(i1)
        """
        self.optimize_loop(ops, expected)
        ops = """
        [i1]
        p1 = new_array_clear(i1, descr=arraydescr)
        i2 = arraylen_gc(p1, descr=arraydescr)
        jump(i2)
        """
        expected = """
        [i1]
        p1 = new_array_clear(i1, descr=arraydescr)
        jump(i1)
        """
        self.optimize_loop(ops, expected)

    def test_nonvirtual_array_write_null_fields_on_force(self):
        ops = """
        [i1]
        p1 = new_array(5, descr=arraydescr)
        setarrayitem_gc(p1, 0, i1, descr=arraydescr)
        setarrayitem_gc(p1, 1, 0, descr=arraydescr)
        jump(p1)
        """
        expected = """
        [i1]
        p1 = new_array(5, descr=arraydescr)
        setarrayitem_gc(p1, 0, i1, descr=arraydescr)
        setarrayitem_gc(p1, 1, 0, descr=arraydescr)
        jump(p1)
        """
        self.optimize_loop(ops, expected)

    def test_varray_forced_1(self):
        ops = """
        []
        p2 = new_with_vtable(descr=nodesize)
        setfield_gc(p2, 3, descr=valuedescr)
        i1 = getfield_gc_i(p2, descr=valuedescr)    # i1 = const 3
        p1 = new_array(i1, descr=arraydescr)
        i2 = arraylen_gc(p1)
        jump(p1, i2)
        """
        # also check that the length of the forced array is known
        expected = """
        []
        p1 = new_array(3, descr=arraydescr)
        jump(p1, 3)
        """
        self.optimize_loop(ops, expected)

    def test_varray_huge_size(self):
        ops = """
        []
        p1 = new_array(150100, descr=arraydescr)
        jump()
        """
        self.optimize_loop(ops, ops)

    def test_varray_negative_items_from_invalid_loop(self):
        ops = """
        [p1, p2]
        i2 = getarrayitem_gc_i(p1, -1, descr=arraydescr)
        setarrayitem_gc(p2, -1, i2, descr=arraydescr)
        jump(p1, p2)
        """
        self.optimize_loop(ops, ops)

    def test_varray_too_large_items(self):
        ops = """
        [p1, p2]
        i2 = getarrayitem_gc_i(p1, 150100, descr=arraydescr)
        i3 = getarrayitem_gc_i(p1, 150100, descr=arraydescr)  # not cached
        setarrayitem_gc(p2, 150100, i2, descr=arraydescr)
        i4 = getarrayitem_gc_i(p2, 150100, descr=arraydescr)  # cached, heap.py
        jump(p1, p2, i3, i4)
        """
        expected = """
        [p1, p2]
        i2 = getarrayitem_gc_i(p1, 150100, descr=arraydescr)
        i3 = getarrayitem_gc_i(p1, 150100, descr=arraydescr)  # not cached
        setarrayitem_gc(p2, 150100, i2, descr=arraydescr)
        jump(p1, p2, i3, i2)
        """
        self.optimize_loop(ops, expected)


    # ____________________________________________________________
    # arrays of structs

    def test_virtual_array_of_struct(self):
        ops = """
        [f0, f1, f2, f3]
        p0 = new_array_clear(2, descr=complexarraydescr)
        setinteriorfield_gc(p0, 0, f1, descr=compleximagdescr)
        setinteriorfield_gc(p0, 0, f0, descr=complexrealdescr)
        setinteriorfield_gc(p0, 1, f3, descr=compleximagdescr)
        setinteriorfield_gc(p0, 1, f2, descr=complexrealdescr)
        f4 = getinteriorfield_gc_f(p0, 0, descr=complexrealdescr)
        f5 = getinteriorfield_gc_f(p0, 1, descr=complexrealdescr)
        f6 = float_mul(f4, f5)
        f7 = getinteriorfield_gc_f(p0, 0, descr=compleximagdescr)
        f8 = getinteriorfield_gc_f(p0, 1, descr=compleximagdescr)
        f9 = float_mul(f7, f8)
        f10 = float_add(f6, f9)
        finish(f10)
        """
        expected = """
        [f0, f1, f2, f3]
        f4 = float_mul(f0, f2)
        f5 = float_mul(f1, f3)
        f6 = float_add(f4, f5)
        finish(f6)
        """
        self.optimize_loop(ops, expected)

    def test_virtual_array_of_struct_forced(self):
        ops = """
        [f0, f1]
        p0 = new_array_clear(1, descr=complexarraydescr)
        setinteriorfield_gc(p0, 0, f0, descr=complexrealdescr)
        setinteriorfield_gc(p0, 0, f1, descr=compleximagdescr)
        f2 = getinteriorfield_gc_f(p0, 0, descr=complexrealdescr)
        f3 = getinteriorfield_gc_f(p0, 0, descr=compleximagdescr)
        f4 = float_mul(f2, f3)
        i0 = escape_i(f4, p0)
        finish(i0)
        """
        expected = """
        [f0, f1]
        f2 = float_mul(f0, f1)
        p0 = new_array_clear(1, descr=complexarraydescr)
        setinteriorfield_gc(p0, 0, f0, descr=complexrealdescr)
        setinteriorfield_gc(p0, 0, f1, descr=compleximagdescr)
        i0 = escape_i(f2, p0)
        finish(i0)
        """
        self.optimize_loop(ops, expected)

    def test_virtual_array_of_struct_len(self):
        ops = """
        []
        p0 = new_array_clear(2, descr=complexarraydescr)
        i0 = arraylen_gc(p0)
        finish(i0)
        """
        expected = """
        []
        finish(2)
        """
        self.optimize_loop(ops, expected)

    def test_virtual_array_of_struct_arraycopy(self):
        ops = """
        [f0, f1]
        p0 = new_array_clear(3, descr=complexarraydescr)
        setinteriorfield_gc(p0, 0, f1, descr=complexrealdescr)
        setinteriorfield_gc(p0, 0, f0, descr=compleximagdescr)
        call_n(0, p0, p0, 0, 2, 1, descr=complexarraycopydescr)
        f2 = getinteriorfield_gc_f(p0, 2, descr=complexrealdescr)
        f3 = getinteriorfield_gc_f(p0, 2, descr=compleximagdescr)
        escape_n(f2)
        escape_n(f3)
        finish(1)
        """
        expected = """
        [f0, f1]
        escape_n(f1)
        escape_n(f0)
        finish(1)
        """
        self.optimize_loop(ops, ops)

    def test_nonvirtual_array_of_struct_arraycopy(self):
        ops = """
        [p0]
        call_n(0, p0, p0, 0, 2, 1, descr=complexarraycopydescr)
        f2 = getinteriorfield_gc_f(p0, 2, descr=compleximagdescr)
        f3 = getinteriorfield_gc_f(p0, 2, descr=complexrealdescr)
        escape_n(f2)
        escape_n(f3)
        finish(1)
        """
        self.optimize_loop(ops, ops)

    def test_varray_huge_size_struct(self):
        ops = """
        []
        p1 = new_array(150100, descr=complexarraydescr)
        jump()
        """
        self.optimize_loop(ops, ops)

    def test_varray_struct_negative_items_from_invalid_loop(self):
        ops = """
        [p1, p2]
        f0 = getinteriorfield_gc_f(p1, -1, descr=complexrealdescr)
        setinteriorfield_gc(p2, -1, f0, descr=compleximagdescr)
        jump(p1, p2)
        """
        self.optimize_loop(ops, ops)

    def test_varray_struct_too_large_items(self):
        ops = """
        [p1, p2]
        f2 = getinteriorfield_gc_f(p1, 150100, descr=compleximagdescr)
        # not cached:
        f3 = getinteriorfield_gc_f(p1, 150100, descr=compleximagdescr)
        setinteriorfield_gc(p2, 150100, f2, descr=complexrealdescr)
        # this is not cached so far (it could be cached by heap.py)
        f4 = getinteriorfield_gc_f(p2, 150100, descr=complexrealdescr)
        jump(p1, p2, f3, f4)
        """
        self.optimize_loop(ops, ops)

