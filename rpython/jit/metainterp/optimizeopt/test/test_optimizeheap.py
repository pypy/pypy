import pytest
from rpython.jit.metainterp.optimizeopt.test.test_optimizebasic import BaseTestBasic

class TestOptimizeHeap(BaseTestBasic):

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

    @pytest.mark.xfail
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
