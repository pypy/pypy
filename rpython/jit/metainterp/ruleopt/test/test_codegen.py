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
with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "real.rules")) as f:
    ALLRULES = f.read()


def test_generate_commutative_rules():
    s = """\
add_zero: int_add(x, 0)
    => x
"""
    ast = parse(s)
    patterns = list(generate_commutative_patterns(ast.rules[0].pattern))
    assert str(patterns[0]) == "int_add(x, 0)"
    assert str(patterns[1]) == "int_add(0, x)"
    assert len(patterns) == 2

    s = """\
add_reassoc_consts: int_add(int_add(x, C1), C2)
    C = C1 + C2
    => int_add(x, C)
"""
    ast = parse(s)
    patterns = list(generate_commutative_patterns(ast.rules[0].pattern))
    assert [str(p) for p in patterns] == [
        'int_add(int_add(x, C1), C2)',
        'int_add(C2, int_add(x, C1))',
        'int_add(int_add(C1, x), C2)',
        'int_add(C2, int_add(C1, x))'
    ]

def test_generate_commutative_rules_only_when_necessary():
    s = """\
or_x_x: int_or(x, x)
    => x
"""
    ast = parse(s)
    patterns = list(generate_commutative_patterns(ast.rules[0].pattern))
    assert str(patterns[0]) == "int_or(x, x)"
    assert len(patterns) == 1

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
    assert [r.name for r in rules] == ['int_sub_zero', 'int_sub_zero_neg', 'int_sub_add', 'int_sub_x_x']

def test_create_matcher():
    s = """\
sub_from_zero: int_sub(0, x)
    => int_neg(x)

sub_add_consts: int_sub(int_add(x, C1), C2)
    C = C2 - C1
    => int_sub(x, C)

sub_add_consts: int_sub(int_add(C1, x), C2)
    C = C2 - C1
    => int_sub(x, C)
    """
    ast = parse(s)
    matcher = create_matcher(ast.rules)
    assert isinstance(matcher, IsConstMatcher)
    assert matcher.name == "arg_0"
    assert matcher.ifyes.rules[0].name == "sub_from_zero"
    assert matcher.ifyes.bindings == {(('int_sub', 0),): 'arg_0', (('int_sub', 1),): 'arg_1', (('int_sub', 0), 'C'): 'C_arg_0'}
    assert matcher.nextmatcher is None
    ifno = matcher.ifno
    assert isinstance(ifno, OpMatcher)
    assert ifno.name == "arg_0"


def test_generate_code_many():
    codegen = Codegen()
    res = codegen.generate_code(parse(ALLRULES))
    print(res)

