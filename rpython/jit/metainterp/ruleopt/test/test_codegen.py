import pytest
try:
    import rply
    import z3
except ImportError:
    pytest.skip('rply or z3 not installed')

from rpython.rlib.rarithmetic import LONG_BIT, r_uint, intmask, ovfcheck, uint_mul_high

from rpython.jit.metainterp.ruleopt.codegen import *
from rpython.jit.metainterp.ruleopt.parse import *

import os
with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "all.rules")) as f:
    ALLRULES = f.read()


def test_generate_commutative_rules():
    s = """\
add_zero: int_add(x, 0)
    => x
"""
    ast = parse(s)
    patterns = list(generate_commutative_patterns(ast.rules[0].pattern))
    assert patterns == [
        PatternOp(
            args=[PatternVar(name="x"), PatternConst(const="0")], opname="int_add"
        ),
        PatternOp(
            args=[PatternConst(const="0"), PatternVar(name="x")], opname="int_add"
        ),
    ]
    assert len(patterns) == 2

    s = """\
add_reassoc_consts: int_add(int_add(x, C1), C2)
    C = C1 + C2
    => int_add(x, C)
"""
    ast = parse(s)
    patterns = list(generate_commutative_patterns(ast.rules[0].pattern))
    assert patterns == [
        PatternOp(
            opname="int_add",
            args=[
                PatternOp(opname="int_add", args=[PatternVar("x"), PatternVar("C1")]),
                PatternVar("C2"),
            ],
        ),
        PatternOp(
            opname="int_add",
            args=[
                PatternVar("C2"),
                PatternOp(opname="int_add", args=[PatternVar("x"), PatternVar("C1")]),
            ],
        ),
        PatternOp(
            opname="int_add",
            args=[
                PatternOp(opname="int_add", args=[PatternVar("C1"), PatternVar("x")]),
                PatternVar("C2"),
            ],
        ),
        PatternOp(
            opname="int_add",
            args=[
                PatternVar("C2"),
                PatternOp(opname="int_add", args=[PatternVar("C1"), PatternVar("x")]),
            ],
        ),
    ]

def test_sort_patterns():
    s = """\
int_sub_zero: int_sub(x, 0)
    => x
int_sub_x_x: int_sub(x, x)
    => 0
int_sub_add: int_sub(int_add(x, y), y)
    => x
int_sub_zero_neg: int_sub(0, x)
    => int_neg(x)
    """
    ast = parse(s)
    rules = sort_rules(ast.rules)
    assert rules == [
        Rule(
            name="int_sub_x_x",
            pattern=PatternOp(
                opname="int_sub", args=[PatternVar("x"), PatternVar("x")]
            ),
            elements=[],
            target=PatternConst("0"),
        ),
        Rule(
            name="int_sub_zero",
            pattern=PatternOp(
                opname="int_sub", args=[PatternVar("x"), PatternConst("0")]
            ),
            elements=[],
            target=PatternVar("x"),
        ),
        Rule(
            name="int_sub_add",
            pattern=PatternOp(
                opname="int_sub",
                args=[
                    PatternOp(
                        opname="int_add", args=[PatternVar("x"), PatternVar("y")]
                    ),
                    PatternVar("y"),
                ],
            ),
            elements=[],
            target=PatternVar("x"),
        ),
        Rule(
            name="int_sub_zero_neg",
            pattern=PatternOp(
                opname="int_sub", args=[PatternConst("0"), PatternVar("x")]
            ),
            elements=[],
            target=PatternOp(opname="int_neg", args=[PatternVar("x")]),
        ),
    ]


def test_generate_code():
    s = """\
sub_zero: int_sub(x, 0)
    => x
sub_x_x: int_sub(x, x)
    => 0
sub_add: int_sub(int_add(x, y), y)
    => x
sub_zero_neg: int_sub(0, x)
    => int_neg(x)
sub_add_consts: int_sub(int_add(x, C1), C2)
    C = C2 - C1
    => int_sub(x, C)
and_x_c_in_range: int_and(x, C)
    check x.lower >= 0 and x.upper <= C & ~(C + 1)
    => x
    """
    codegen = Codegen()
    res = codegen.generate_code(parse(s))
    print(res)
    assert (
        res
        == """
def optimize_INT_SUB(self, op):
    arg_0 = get_box_replacement(op.getarg(0))
    b_arg_0 = self.getintbound(arg_0)
    arg_1 = get_box_replacement(op.getarg(1))
    b_arg_1 = self.getintbound(arg_1)
    # sub_x_x: int_sub(x, x) => 0
    if arg_1 is arg_0:
        self.make_constant_int(op, 0)
        return
    # sub_zero: int_sub(x, 0) => x
    if b_arg_1.known_eq_const(0):
        self.make_equal_to(op, arg_0)
        return
    # sub_add: int_sub(int_add(x, y), y) => x
    arg_0_int_add = self.optimizer.as_operation(arg_0, rop.INT_ADD)
    if arg_0_int_add is not None:
        arg_0_int_add_0 = get_box_replacement(arg_0.getarg(0))
        b_arg_0_int_add_0 = self.getintbound(arg_0_int_add_0)
        arg_0_int_add_1 = get_box_replacement(arg_0.getarg(1))
        b_arg_0_int_add_1 = self.getintbound(arg_0_int_add_1)
        if arg_1 is arg_0_int_add_1:
            self.make_equal_to(op, arg_0_int_add_0)
            return
    # sub_add: int_sub(int_add(y, x), y) => x
    arg_0_int_add = self.optimizer.as_operation(arg_0, rop.INT_ADD)
    if arg_0_int_add is not None:
        arg_0_int_add_0 = get_box_replacement(arg_0.getarg(0))
        b_arg_0_int_add_0 = self.getintbound(arg_0_int_add_0)
        arg_0_int_add_1 = get_box_replacement(arg_0.getarg(1))
        b_arg_0_int_add_1 = self.getintbound(arg_0_int_add_1)
        if arg_1 is arg_0_int_add_0:
            self.make_equal_to(op, arg_0_int_add_1)
            return
    # sub_zero_neg: int_sub(0, x) => int_neg(x)
    if b_arg_0.known_eq_const(0):
        newop = self.replace_op_with(op, rop.INT_NEG, args=[arg_1])
        self.optimizer.send_extra_operation(newop)
        return
    # sub_add_consts: int_sub(int_add(x, C1), C2) => int_sub(x, C)
    arg_0_int_add = self.optimizer.as_operation(arg_0, rop.INT_ADD)
    if arg_0_int_add is not None:
        arg_0_int_add_0 = get_box_replacement(arg_0.getarg(0))
        b_arg_0_int_add_0 = self.getintbound(arg_0_int_add_0)
        arg_0_int_add_1 = get_box_replacement(arg_0.getarg(1))
        b_arg_0_int_add_1 = self.getintbound(arg_0_int_add_1)
        if b_arg_0_int_add_1.is_constant():
            C_arg_0_int_add_1 = b_arg_0_int_add_1.get_constant_int()
            if b_arg_1.is_constant():
                C_arg_1 = b_arg_1.get_constant_int()
                C = intmask(r_uint(C_arg_1) - r_uint(C_arg_0_int_add_1))
                newop = self.replace_op_with(op, rop.INT_SUB, args=[arg_0_int_add_0, ConstInt(C)])
                self.optimizer.send_extra_operation(newop)
                return
    # sub_add_consts: int_sub(int_add(C1, x), C2) => int_sub(x, C)
    arg_0_int_add = self.optimizer.as_operation(arg_0, rop.INT_ADD)
    if arg_0_int_add is not None:
        arg_0_int_add_0 = get_box_replacement(arg_0.getarg(0))
        b_arg_0_int_add_0 = self.getintbound(arg_0_int_add_0)
        arg_0_int_add_1 = get_box_replacement(arg_0.getarg(1))
        b_arg_0_int_add_1 = self.getintbound(arg_0_int_add_1)
        if b_arg_0_int_add_0.is_constant():
            C_arg_0_int_add_0 = b_arg_0_int_add_0.get_constant_int()
            if b_arg_1.is_constant():
                C_arg_1 = b_arg_1.get_constant_int()
                C = intmask(r_uint(C_arg_1) - r_uint(C_arg_0_int_add_0))
                newop = self.replace_op_with(op, rop.INT_SUB, args=[arg_0_int_add_1, ConstInt(C)])
                self.optimizer.send_extra_operation(newop)
                return
    return self.emit(op)

def optimize_INT_AND(self, op):
    arg_0 = get_box_replacement(op.getarg(0))
    b_arg_0 = self.getintbound(arg_0)
    arg_1 = get_box_replacement(op.getarg(1))
    b_arg_1 = self.getintbound(arg_1)
    # and_x_c_in_range: int_and(x, C) => x
    if b_arg_1.is_constant():
        C_arg_1 = b_arg_1.get_constant_int()
        if x.lower >= 0 and x.upper <= C_arg_1 & ~intmask(r_uint(C_arg_1) + r_uint(1)):
            self.make_equal_to(op, arg_0)
            return
    return self.emit(op)
"""
    )

def test_generate_code_many():
    codegen = Codegen()
    res = codegen.generate_code(parse(ALLRULES))
    print(res)

