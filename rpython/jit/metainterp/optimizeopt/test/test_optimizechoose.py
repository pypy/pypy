import pytest
from rpython.jit.metainterp.optimizeopt.test.test_optimizebasic import BaseTestBasic
from rpython.jit.metainterp.optimizeopt.intutils import MININT, MAXINT
from rpython.jit.metainterp.optimizeopt.intdiv import magic_numbers
from rpython.rlib.rarithmetic import intmask, LONG_BIT


class TestOptimize(BaseTestBasic):
    def test_jit_choose_constant(self):
        ops = """
        [i1]
        i2 = jit_choose_i(0, 4, 5)
        i3 = jit_choose_i(1, 4, 5)
        jump(i2, i3)
        """
        expected = """
        [i1]
        jump(4, 5)
        """
        self.optimize_loop(ops, expected)

    def test_jit_choose_r_propagate_class(self):
        ops = """
        [i1]
        p0 = jit_choose_r(i1, ConstPtr(myptr), ConstPtr(myptrb))
        guard_nonnull(p0) []
        guard_class(p0, ConstClass(node_vtable)) []
        jump(p0)
        """
        expected = """
        [i1]
        p0 = jit_choose_r(i1, ConstPtr(myptr), ConstPtr(myptrb))
        jump(p0)
        """
        self.optimize_loop(ops, expected)

    def test_jit_choose_r_cant_propagate_class(self):
        ops = """
        [i1]
        p0 = jit_choose_r(i1, ConstPtr(myptr), ConstPtr(myptr2))
        guard_nonnull(p0) []
        guard_class(p0, ConstClass(node_vtable)) []
        jump(p0)
        """
        expected = """
        [i1]
        p0 = jit_choose_r(i1, ConstPtr(myptr), ConstPtr(myptr2))
        guard_class(p0, ConstClass(node_vtable)) []
        jump(p0)
        """
        self.optimize_loop(ops, expected)


    def test_jit_choose_promote(self):
        ops = """
        [i1]
        i2 = jit_choose_i(i1, 0, 1)
        guard_value(i2, 0) []
        finish(i1)
        """
        expected = """
        [i1]
        i2 = jit_choose_i(i1, 0, 1)
        guard_value(i1, 0) []
        finish(0)
        """
        self.optimize_loop(ops, expected)

    def test_jit_choose_pure(self):
        ops = """
        [i1]
        i2 = jit_choose_i(i1, 0, 1)
        i3 = jit_choose_i(i1, 0, 1)
        jump(i2, i3)
        """
        expected = """
        [i1]
        i2 = jit_choose_i(i1, 0, 1)
        jump(i2, i2)
        """
        self.optimize_loop(ops, expected)

