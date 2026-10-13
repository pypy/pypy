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


@pytest.mark.parametrize("opname, args, expected_args", [
    ("int_add", [PatternVar("x", IntBound), PatternVar("C", int)],
     "Ref(Value('x')), Call(Symbol('ConstInt'), [Ref(Value('C'))], [])"),
    ("int_sub", [PatternVar("x", IntBound), PatternVar("y", IntBound)],
     "Ref(Value('x')), Ref(Value('y'))"),
    ("int_and", [PatternVar("x", IntBound), PatternConst("MININT")],
     "Ref(Value('x')), Call(Symbol('ConstInt'), [Symbol('MININT')], [])"),
    ("int_neg", [PatternConst("0")],
     "Call(Symbol('ConstInt'), [Literal(0)], [])"),
])
def test_lower_operation_target(opname, args, expected_args):
    from rpython.jit.metainterp.ruleopt import ir

    bindings = dict((name, ir.Value(name)) for name in ("x", "y", "C"))
    builder = IRCodegen(ir.Value("self"), ir.Value("op"), bindings)
    builder.generate_target(PatternOp(opname, args))
    assert repr(builder.block) == (
        "Block([Bind(Value('newop'), "
        "Call(Attribute(Ref(Value('self')), 'replace_op_with'), "
        "[Ref(Value('op')), Attribute(Symbol('rop'), %r)], "
        "[('args', ListExpr([%s]))])), "
        "ExprStmt(Call(Attribute(Attribute(Ref(Value('self')), 'optimizer'), "
        "'send_extra_operation'), [Ref(Value('newop'))], []))])"
        % (opname.upper(), expected_args))


@pytest.mark.parametrize("expr, expected", [
    (Number(7), "Literal(7)"),
    (Name("C", int), "Ref(Value('constant'))"),
    (Name("x", IntBound), "Ref(Value('bound_x'))"),
    (Name("LONG_BIT", int), "Symbol('LONG_BIT')"),
    (Eq(Name("C", int), Number(0)),
     "Binary('==', Ref(Value('constant')), Literal(0))"),
    (OpAnd(Name("C", int), Number(3)),
     "Binary('&', Ref(Value('constant')), Literal(3))"),
    (Add(Name("C", int), Number(1)),
     "Call(Symbol('intmask'), [Binary('+', "
     "Call(Symbol('r_uint'), [Ref(Value('constant'))], []), "
     "Call(Symbol('r_uint'), [Literal(1)], []))], [])"),
    (URShift(Name("C", int), Number(1)),
     "Call(Symbol('intmask'), [Binary('>>', "
     "Call(Symbol('r_uint'), [Ref(Value('constant'))], []), "
     "Call(Symbol('r_uint'), [Literal(1)], []))], [])"),
    (ARShift(Name("C", int), Number(1)),
     "Binary('>>', Ref(Value('constant')), Literal(1))"),
    (MethodCall(Name("x", IntBound), "is_bool", []),
     "Call(Attribute(Ref(Value('bound_x')), 'is_bool'), [], [])"),
    (MethodCall(Name("x", IntBound), "known_ge_const", [Number(0)]),
     "Call(Attribute(Ref(Value('bound_x')), 'known_ge_const'), "
     "[Literal(0)], [])"),
    (MethodCall(
        MethodCall(Name("x", IntBound), "and_bound", [Name("x", IntBound)]),
        "known_eq_const", [Number(0)]),
     "Call(Attribute(Call(Attribute(Ref(Value('bound_x')), 'and_bound'), "
     "[Ref(Value('bound_x'))], []), 'known_eq_const'), [Literal(0)], [])"),
    (FuncCall("highest_bit", [Name("C", int)]),
     "Call(Symbol('highest_bit'), [Ref(Value('constant'))], [])"),
    (FuncCall("min", [Name("C", int), Number(3)]),
     "Call(Symbol('min'), [Ref(Value('constant')), Literal(3)], [])"),
])
def test_lower_expression(expr, expected):
    from rpython.jit.metainterp.ruleopt import ir

    builder = IRCodegen(
        ir.Value("self"), ir.Value("op"),
        {"C": ir.Value("constant"), "x": ir.Value("box_x")},
        {"x": ir.Value("bound_x")})
    assert repr(builder.visit(expr)) == expected
    # Expression lowering returns a tree; it doesn't emit statements.
    assert repr(builder.block) == "Block([])"


@pytest.mark.parametrize("attrname, expected", [
    ("lower",
     "Call(Symbol('intmask'), [Attribute(Ref(Value('bound_x')), 'lower')], [])"),
    ("tmask",
     "Call(Symbol('intmask'), [Attribute(Ref(Value('bound_x')), 'tmask')], [])"),
    ("ones",
     "Call(Symbol('intmask'), [Attribute(Ref(Value('bound_x')), 'tvalue')], [])"),
    ("zeros",
     "Call(Symbol('intmask'), [Unary('~', Binary('|', "
     "Attribute(Ref(Value('bound_x')), 'tvalue'), "
     "Attribute(Ref(Value('bound_x')), 'tmask')))], [])"),
])
def test_lower_bound_attribute(attrname, expected):
    from rpython.jit.metainterp.ruleopt import ir

    builder = IRCodegen(ir.Value("self"), ir.Value("op"),
                        {"x": ir.Value("box_x")},
                        {"x": ir.Value("bound_x")})
    assert repr(builder.visit(Attribute("x", attrname))) == expected
    assert repr(builder.block) == "Block([])"
