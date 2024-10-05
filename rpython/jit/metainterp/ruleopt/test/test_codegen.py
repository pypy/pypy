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
            cantproof=False,
            name="int_sub_x_x",
            pattern=PatternOp(
                opname="int_sub", args=[PatternVar("x"), PatternVar("x")]
            ),
            elements=[],
            target=PatternConst("0"),
        ),
        Rule(
            cantproof=False,
            name="int_sub_zero",
            pattern=PatternOp(
                opname="int_sub", args=[PatternVar("x"), PatternConst("0")]
            ),
            elements=[],
            target=PatternVar("x"),
        ),
        Rule(
            cantproof=False,
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
            cantproof=False,
            name="int_sub_zero_neg",
            pattern=PatternOp(
                opname="int_sub", args=[PatternConst("0"), PatternVar("x")]
            ),
            elements=[],
            target=PatternOp(opname="int_neg", args=[PatternVar("x")]),
        ),
    ]

def test_generate_code_many():
    codegen = Codegen()
    res = codegen.generate_code(parse(ALLRULES))
    print(res)

