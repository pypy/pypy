import pytest

try:
    import rply
except ImportError:
    pytest.skip("rply not installed")

from rpython.jit.metainterp.ruleopt.parse import *

import os

with open(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "all.rules"
    )
) as f:
    ALLRULES = f.read()


def test_parse_int_add_zero():
    s = """\
add_zero: int_add(x, 0)
    => x
"""
    ast = parse(s)
    assert ast == File(
        rules=[
            Rule(
                elements=[],
                cantproof=False,
                name="add_zero",
                pattern=PatternOp(
                    args=[PatternVar(name="x"), PatternConst(const="0")],
                    opname="int_add",
                ),
                target=PatternVar(name="x"),
            )
        ]
    )


def test_parse_int_add_zero():
    s = """\
add_reassoc_consts: int_add(int_add(x, C1), C2)
    C = C1 + C2
    => int_add(x, C)
"""
    ast = parse(s)
    assert ast == File(
        rules=[
            Rule(
                cantproof=False,
                elements=[
                    Compute(
                        expr=Add(left=Name(name="C1"), right=Name(name="C2")), name="C"
                    )
                ],
                name="add_reassoc_consts",
                pattern=PatternOp(
                    args=[
                        PatternOp(
                            args=[PatternVar(name="x"), PatternVar(name="C1")],
                            opname="int_add",
                        ),
                        PatternVar(name="C2"),
                    ],
                    opname="int_add",
                ),
                target=PatternOp(
                    args=[PatternVar(name="x"), PatternVar(name="C")], opname="int_add"
                ),
            )
        ]
    )


def test_parse_int_mul():
    s = """\
mul_zero: int_mul(x, 0)
    => 0

mul_one: int_mul(x, 1)
    => 1

mul_minus_one: int_mul(x, -1)
    => int_neg(x)

mul_neg_neg: int_mul(int_neg(x), int_neg(y))
    => int_mul(x, y)
"""
    ast = parse(s)
    assert ast == File(
        rules=[
            Rule(
                cantproof=False,
                elements=[],
                name="mul_zero",
                pattern=PatternOp(
                    args=[PatternVar(name="x"), PatternConst(const="0")],
                    opname="int_mul",
                ),
                target=PatternConst(const="0"),
            ),
            Rule(
                cantproof=False,
                elements=[],
                name="mul_one",
                pattern=PatternOp(
                    args=[PatternVar(name="x"), PatternConst(const="1")],
                    opname="int_mul",
                ),
                target=PatternConst(const="1"),
            ),
            Rule(
                cantproof=False,
                elements=[],
                name="mul_minus_one",
                pattern=PatternOp(
                    args=[PatternVar(name="x"), PatternConst(const="-1")],
                    opname="int_mul",
                ),
                target=PatternOp(args=[PatternVar(name="x")], opname="int_neg"),
            ),
            Rule(
                cantproof=False,
                elements=[],
                name="mul_neg_neg",
                pattern=PatternOp(
                    args=[
                        PatternOp(args=[PatternVar(name="x")], opname="int_neg"),
                        PatternOp(args=[PatternVar(name="y")], opname="int_neg"),
                    ],
                    opname="int_mul",
                ),
                target=PatternOp(
                    args=[PatternVar(name="x"), PatternVar(name="y")], opname="int_mul"
                ),
            ),
        ]
    )


def test_parse_function_many_args():
    s = """\
n: op(C)
    C1 = f(C, C, C, C)
    => C
    """
    ast = parse(s)


def test_sorry():
    s = """\
eq_different_knownbits: int_eq(x, y)
    SORRY_Z3
    => 0
    """
    ast = parse(s)
    assert ast == File(
        [
            Rule(
                name="eq_different_knownbits",
                pattern=PatternOp(
                    opname="int_eq", args=[PatternVar("x"), PatternVar("y")]
                ),
                cantproof=True,
                elements=[],
                target=PatternConst("0"),
            )
        ]
    )


def test_parse_lshift_rshift():
    s = """\
int_lshift_int_rshift_consts: int_lshift(int_rshift(x, C1), C1)
    C = (-1 >>a C1) << C1
    => int_and(x, C)
    """
    ast = parse(s)


def test_parse_lshift_rshift():
    s = """\
eq_different_knownbits: int_eq(x, y)
    SORRY_Z3
    => 0
    """
    ast = parse(s)
    assert ast == File(
        [
            Rule(
                name="eq_different_knownbits",
                pattern=PatternOp(
                    opname="int_eq", args=[PatternVar("x"), PatternVar("y")]
                ),
                cantproof=True,
                elements=[],
                target=PatternConst("0"),
            )
        ]
    )


def test_parse_all():
    ast = parse(ALLRULES)  # also typechecks


def test_undefined_name():
    s = """\
n: op(C)
    => x
    """
    with pytest.raises(TypeCheckError) as info:
        ast = parse(s)
    assert str(info.value) == "variable 'x' is not defined"


def test_doubly_defined_name():
    s = """\
n: op(C)
    C = C + 1
    => C
    """
    with pytest.raises(TypeCheckError) as info:
        ast = parse(s)
    assert str(info.value) == "'C' is already defined"


def test_check_not_bool():
    s = """\
n: op(C)
    check C
    => C
    """
    with pytest.raises(TypeCheckError) as info:
        ast = parse(s)
    assert str(info.value) == "expected check expression to return a bool, got int"
