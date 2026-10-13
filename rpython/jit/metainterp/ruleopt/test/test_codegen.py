import pytest
try:
    import rply
    import z3
except ImportError:
    pytest.skip('rply or z3 not installed', allow_module_level=True)

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


def test_generate_unary_minus_safe_for_minint():
    s = """\
sub_const_canonicalize: int_sub(x, C1)
    C = -C1
    => int_add(x, C)
"""
    codegen = Codegen()
    res = codegen.generate_code(parse(s))
    # must not contain a naive "-C_arg_1" negation, which overflows for
    # MININT; must use the wraparound-safe r_uint-based form instead
    assert "intmask(-r_uint(" in res
    assert "-C_arg_1" not in res


@pytest.mark.parametrize("target, expected", [
    (PatternVar("x", IntBound),
     "Block([ExprStmt(Call(Attribute(Ref(Value('self')), 'make_equal_to'), "
     "[Ref(Value('op')), Ref(Value('x'))], []))])"),
    (PatternConst("0"),
     "Block([ExprStmt(Call(Attribute(Ref(Value('self')), 'make_constant_int'), "
     "[Ref(Value('op')), Literal(0)], []))])"),
])
def test_lower_simple_target(target, expected):
    from rpython.jit.metainterp.ruleopt import ir

    builder = IRCodegen(ir.Value("self"), ir.Value("op"), {"x": ir.Value("x")})
    builder.generate_target(target)
    assert repr(builder.block) == expected


@pytest.mark.parametrize("name", ["C", "computed"])
def test_lower_integer_target(name):
    from rpython.jit.metainterp.ruleopt import ir

    builder = IRCodegen(ir.Value("self"), ir.Value("op"),
                        {name: ir.Value("constant")})
    builder.generate_target(PatternVar(name, int))
    assert repr(builder.block) == (
        "Block([ExprStmt(Call(Attribute(Ref(Value('self')), 'make_equal_to'), "
        "[Ref(Value('op')), Call(Symbol('ConstInt'), "
        "[Ref(Value('constant'))], [])], []))])")


@pytest.mark.parametrize("name", ["MININT", "MAXINT", "LONG_BIT"])
def test_lower_named_constant_target(name):
    from rpython.jit.metainterp.ruleopt import ir

    builder = IRCodegen(ir.Value("self"), ir.Value("op"), {})
    builder.generate_target(PatternConst(name))
    assert repr(builder.block) == (
        "Block([ExprStmt(Call(Attribute(Ref(Value('self')), 'make_constant_int'), "
        "[Ref(Value('op')), Symbol(%r)], []))])" % name)


def test_lower_target_requires_existing_binding():
    from rpython.jit.metainterp.ruleopt import ir

    builder = IRCodegen(ir.Value("self"), ir.Value("op"), {})
    with pytest.raises(KeyError):
        builder.generate_target(PatternVar("missing", IntBound))
    assert builder.bindings == {}
    assert repr(builder.block) == "Block([])"
