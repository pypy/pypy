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


@pytest.mark.parametrize('source, expected_path', [
    ("and_absorb: int_and(a, int_and(a, b)) => int_and(a, b)",
     (('int_and', 1),)),
    ("and_absorb_commuted: int_and(a, int_and(b, a)) => int_and(a, b)",
     (('int_and', 1),)),
    ("nested: int_add(int_neg(int_sub(a, b)), c) => int_sub(a, b)",
     (('int_add', 0), ('int_neg', 0))),
    ("constant: int_add(int_sub(a, 1), b) => int_sub(a, 1)",
     (('int_add', 0),)),
    ("different_constant: int_add(int_sub(a, 1), b) => int_sub(a, 2)", None),
    ("different_variable: int_add(int_sub(a, b), c) => int_sub(a, c)", None),
    ("different_op: int_add(int_sub(a, b), c) => int_add(a, b)", None),
    ("reversed: int_add(int_sub(a, b), c) => int_sub(b, a)", None),
    ("root_only: int_sub(a, b) => int_sub(a, b)", None),
    ("variable_target: int_and(a, int_and(a, b)) => a", None),
    ("first: int_add(int_sub(a, b), int_sub(a, b)) => int_sub(a, b)",
     (('int_add', 0),)),
])
def test_find_reusable_operation(source, expected_path):
    # These examples test syntax matching, not the validity of rewrite rules.
    rule = parse(source.replace(' => ', '\n    => ') + '\n').rules[0]
    assert find_reusable_operation(rule.pattern, rule.target) == expected_path


def test_find_reusable_operation_ignores_variable_type_annotations():
    pattern = PatternOp('int_and', [PatternVar('a'), PatternOp('int_and', [
        PatternVar('a'), PatternVar('b')])])
    target = PatternOp('int_and', [PatternVar('a', IntBound),
                                  PatternVar('b', IntBound)])
    assert find_reusable_operation(pattern, target) == (('int_and', 1),)

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


@pytest.mark.parametrize("literal", ["0", "1", "-1", "42", "MININT", "MAXINT", "LONG_BIT"])
@pytest.mark.parametrize("operation_target", [False, True])
def test_literal_boxes_are_prebuilt(literal, operation_target):
    from rpython.jit.metainterp.history import ConstInt, CONST_FALSE, CONST_TRUE
    from rpython.jit.metainterp.resoperation import rop
    import sys
    MAXINT = sys.maxint
    MININT = -MAXINT - 1

    target = "int_add(x, %s)" % literal if operation_target else literal
    source = "example: int_neg(x)\n    => %s\n" % target
    namespace = dict(ConstInt=ConstInt, CONST_FALSE=CONST_FALSE,
                     CONST_TRUE=CONST_TRUE, MININT=MININT, MAXINT=MAXINT,
                     LONG_BIT=LONG_BIT, rop=rop,
                     get_box_replacement=lambda box: box)
    code = Codegen().generate_mixin(parse(source))
    exec compile(code, '<generated rules>', 'exec') in namespace

    def no_allocation(value):
        pytest.fail("allocated ConstInt while executing a generated method")
    namespace['ConstInt'] = no_allocation

    class Recorder(namespace['OptIntAutoGenerated']):
        def make_constant(self, op, value):
            self.result = value

        def _replace_op_with_2_and_send(self, op, opnum, arg0, arg1):
            assert opnum == rop.INT_ADD
            self.result = arg1

    class Operation(object):
        def getarg(self, index):
            return CONST_TRUE

    first, second = Recorder(), Recorder()
    first.optimize_INT_NEG(Operation())
    second.optimize_INT_NEG(Operation())
    assert first.result is second.result
    expected = {"MININT": MININT, "MAXINT": MAXINT, "LONG_BIT": LONG_BIT}
    value = expected[literal] if literal in expected else int(literal)
    assert first.result.getint() == value
    if value in (0, 1):
        assert first.result is (CONST_TRUE if value else CONST_FALSE)


def test_method_generation_uses_ir(monkeypatch):
    from rpython.jit.metainterp.ruleopt import ir

    rule = Rule("example", PatternOp("int_add", [PatternVar("x"), PatternConst("0")]),
                False, [], PatternVar("x", IntBound))
    calls = []

    def generate_method(builder, opname, rules):
        calls.append((opname, rules))
        builder.rule_names = ["example"]
        return ir.Block([
            ir.Bind(ir.Value('unused'), ir.Literal(456)),
            ir.Return(ir.Literal(123)),
        ])

    monkeypatch.setattr(IRCodegen, "generate_method", generate_method)
    generator = Codegen()
    generator.generate_method("int_add", [rule])
    assert calls == [("int_add", [rule])]
    assert "_rule_names_int_add = ['example']" in generator.code
    assert "_rule_fired_int_add = [0] * 1" in generator.code
    assert "def optimize_INT_ADD(self, op):" in generator.code
    assert "    return 123" in generator.code
    assert "    unused = 456" not in generator.code


def test_method_generation_moves_bindings_down(monkeypatch):
    value = ir.Value('result')
    binding = ir.Bind(value, ir.Literal(123))
    branch = ir.If(ir.Symbol('condition'), ir.Block([ir.Return()]), ir.Block([]))
    ret = ir.Return(ir.Ref(value))
    body = ir.Block([binding, branch, ret])
    monkeypatch.setattr(IRCodegen, 'generate_method',
                        lambda builder, opname, rules: body)
    Codegen().generate_method('int_add', [])
    assert body.statements == [branch, binding, ret]


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
     "Block([ExprStmt(Call(Attribute(Ref(Value('self')), 'make_constant'), "
     "[Ref(Value('op')), Symbol('CONST_FALSE')], []))])"),
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
        "Block([ExprStmt(Call(Attribute(Ref(Value('self')), 'make_constant'), "
        "[Ref(Value('op')), Symbol(%r)], []))])" % ("CONST_" + name))


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
     "Ref(Value('x')), Symbol('CONST_MININT')"),
    ("int_neg", [PatternConst("0")],
     "Symbol('CONST_FALSE')"),
])
def test_lower_operation_target(opname, args, expected_args):
    from rpython.jit.metainterp.ruleopt import ir

    bindings = dict((name, ir.Value(name)) for name in ("x", "y", "C"))
    builder = IRCodegen(ir.Value("self"), ir.Value("op"), bindings)
    builder.generate_target(PatternOp(opname, args))
    assert repr(builder.block) == (
        "Block([ExprStmt(Call(Attribute(Ref(Value('self')), '_replace_op_with_%d_and_send'), "
        "[Ref(Value('op')), Attribute(Symbol('rop'), %r), %s], "
        "[], side_effects=True))])"
        % (len(args), opname.upper(), expected_args))


@pytest.mark.parametrize("expr, expected", [
    (Number(7), "Literal(7)"),
    (Name("C", int), "Ref(Value('constant'))"),
    (Name("x", IntBound), "Ref(Value('bound_x'))"),
    (Name("LONG_BIT", int), "Symbol('LONG_BIT')"),
    (Invert(Name("C", int)), "Unary('~', Ref(Value('constant')))"),
    (Neg(Name("C", int)),
     "Call(Symbol('intmask'), [Unary('-', "
     "Call(Symbol('r_uint'), [Ref(Value('constant'))], []))], [])"),
    (Invert(Neg(Number(1))),
     "Unary('~', Call(Symbol('intmask'), [Unary('-', "
     "Call(Symbol('r_uint'), [Literal(1)], []))], []))"),
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


def test_lower_computation_body():
    from rpython.jit.metainterp.ruleopt import ir

    builder = IRCodegen(ir.Value("self"), ir.Value("op"), {})
    builder.generate_body([Compute("C", Number(7))], PatternVar("C", int))
    assert repr(builder.block) == (
        "Block([Bind(Value('C'), Literal(7)), "
        "ExprStmt(Call(Attribute(Ref(Value('self')), 'make_equal_to'), "
        "[Ref(Value('op')), Call(Symbol('ConstInt'), [Ref(Value('C'))], [])], []))])")
    assert builder.bindings == {}


def test_ir_emit_uses_current_block():
    from rpython.jit.metainterp.ruleopt import ir

    builder = IRCodegen(ir.Value("self"), ir.Value("op"), {})
    outer = builder.block
    branch = ir.If(ir.Literal(True), ir.Block([]), ir.Block([]))
    builder.emit(branch)
    builder.block = branch.then_block
    builder.emit(ir.Return())
    assert repr(outer) == (
        "Block([If(Literal(True), Block([Return(None)]), Block([]))])")


def test_checks_nest_the_remaining_body():
    from rpython.jit.metainterp.ruleopt import ir

    builder = IRCodegen(ir.Value("self"), ir.Value("op"),
                        {"C": ir.Value("constant")})
    outer_block = builder.block
    builder.generate_body([
        Check(Gt(Name("C", int), Number(0))),
        Compute("D", Number(7)),
        Check(Lt(Name("D", int), Number(10))),
    ], PatternVar("D", int))
    assert builder.block is outer_block
    assert repr(builder.block) == (
        "Block([If(Binary('>', Ref(Value('constant')), Literal(0)), "
        "Block([Bind(Value('D'), Literal(7)), "
        "If(Binary('<', Ref(Value('D')), Literal(10)), "
        "Block([ExprStmt(Call(Attribute(Ref(Value('self')), 'make_equal_to'), "
        "[Ref(Value('op')), Call(Symbol('ConstInt'), [Ref(Value('D'))], [])], []))]), "
        "Block([]))]), Block([]))])")
    assert "D" not in builder.bindings


def test_computed_bound_is_available_to_checks():
    from rpython.jit.metainterp.ruleopt import ir

    builder = IRCodegen(ir.Value("self"), ir.Value("op"),
                        {"x": ir.Value("box_x")},
                        {"x": ir.Value("bound_x")})
    builder.generate_body([
        Compute("bound", Name("x", IntBound)),
        Check(MethodCall(Name("bound", IntBound), "is_constant", [])),
    ], PatternConst("0"))
    assert repr(builder.block) == (
        "Block([Bind(Value('bound'), Ref(Value('bound_x'))), "
        "If(Call(Attribute(Ref(Value('bound')), 'is_constant'), [], []), "
        "Block([ExprStmt(Call(Attribute(Ref(Value('self')), 'make_constant'), "
        "[Ref(Value('op')), Symbol('CONST_FALSE')], []))]), Block([]))])")
    assert "bound" not in builder.intbound_bindings


def test_finished_rule_body():
    from rpython.jit.metainterp.ruleopt import ir

    rule = Rule("eq_one", PatternOp("int_eq", [PatternVar("x"), PatternConst("1")]),
                False, [Check(MethodCall(Name("x", IntBound), "is_bool", []))],
                PatternVar("x", IntBound))
    builder = IRCodegen(ir.Value("self"), ir.Value("op"),
                        {"x": ir.Value("box_x")},
                        {"x": ir.Value("bound_x")})
    builder.generate_rule_body(rule, "int_eq", 2)
    assert repr(builder.block) == (
        "Block([If(Call(Attribute(Ref(Value('bound_x')), 'is_bool'), [], []), "
        "Block([ExprStmt(Call(Attribute(Ref(Value('self')), 'make_equal_to'), "
        "[Ref(Value('op')), Ref(Value('box_x'))], [])), "
        "FinishRule(Ref(Value('self')), 'int_eq', 2, "
        "'eq_one: int_eq(x, 1) => x')]), Block([]))])")


def test_ir_argument_reads():
    from rpython.jit.metainterp.ruleopt import ir

    builder = IRCodegen(ir.Value("self"), ir.Value("op"), {})
    boxes, bounds = builder.emit_arg_reads(builder.op_ref, 2, prefix="arg_0")
    assert repr(boxes) == "[Value('arg_0_0'), Value('arg_0_1')]"
    assert repr(bounds) == "[Value('b_arg_0_0'), Value('b_arg_0_1')]"
    assert repr(builder.block) == (
        "Block([Bind(Value('arg_0_0'), Call(Symbol('get_box_replacement'), "
        "[Call(Attribute(Ref(Value('op')), 'getarg'), [Literal(0)], [])], [])), "
        "Bind(Value('b_arg_0_0'), Call(Attribute(Ref(Value('self')), 'getintbound'), "
        "[Ref(Value('arg_0_0'))], [])), "
        "Bind(Value('arg_0_1'), Call(Symbol('get_box_replacement'), "
        "[Call(Attribute(Ref(Value('op')), 'getarg'), [Literal(1)], [])], [])), "
        "Bind(Value('b_arg_0_1'), Call(Attribute(Ref(Value('self')), 'getintbound'), "
        "[Ref(Value('arg_0_1'))], []))])")
    assert builder.bindings == {}
    assert builder.intbound_bindings == {}


def test_ir_argument_reads_empty():
    from rpython.jit.metainterp.ruleopt import ir

    builder = IRCodegen(ir.Value("self"), ir.Value("op"), {})
    assert builder.emit_arg_reads(builder.op_ref, 0) == ([], [])
    assert repr(builder.block) == "Block([])"


@pytest.mark.parametrize("with_fallbacks", [False, True])
def test_ir_constant_matcher(with_fallbacks):
    from rpython.jit.metainterp.ruleopt import ir

    # Stand-ins for child matchers isolate this visitor from terminal lowering.
    class Marker(BaseMatcher):
        def __init__(self, name):
            self.name = name

    class MarkerCodegen(IRCodegen):
        def visit_Marker(self, marker):
            args = []
            if marker.name == "yes":
                args.append(ir.Ref(self.matcher_values["C_arg_0"]))
            else:
                assert "C_arg_0" not in self.matcher_values
            self.emit(ir.ExprStmt(ir.Call(ir.Symbol(marker.name), args)))

    builder = MarkerCodegen(ir.Value("self"), ir.Value("op"), {})
    values = {"arg_0": ir.Value("arg_0"), "b_arg_0": ir.Value("b_arg_0")}
    builder.matcher_values = values
    outer_block = builder.block
    builder.visit(IsConstMatcher(
        "arg_0", Marker("yes"),
        Marker("no") if with_fallbacks else None,
        Marker("next") if with_fallbacks else None, "C_arg_0"))
    expected_else = (
        "Block([ExprStmt(Call(Symbol('no'), [], []))])"
        if with_fallbacks else "Block([])")
    expected_next = (
        ", ExprStmt(Call(Symbol('next'), [], []))" if with_fallbacks else "")
    assert repr(builder.block) == (
        "Block([If(Call(Attribute(Ref(Value('b_arg_0')), 'is_constant'), [], []), "
        "Block([Bind(Value('C_arg_0'), "
        "Call(Attribute(Ref(Value('b_arg_0')), 'get_constant_int'), [], [])), "
        "ExprStmt(Call(Symbol('yes'), [Ref(Value('C_arg_0'))], []))]), "
        "%s)%s])" % (expected_else, expected_next))
    assert builder.block is outer_block
    assert builder.matcher_values is values
    assert "C_arg_0" not in values


@pytest.mark.parametrize("with_fallbacks", [False, True])
def test_ir_operation_matcher(with_fallbacks):
    from rpython.jit.metainterp.ruleopt import ir

    class Marker(BaseMatcher):
        def __init__(self, name):
            self.name = name

    class MarkerCodegen(IRCodegen):
        def visit_Marker(self, marker):
            args = []
            if marker.name == "yes":
                args = [ir.Ref(self.matcher_values[name])
                        for name in ("arg_0_0", "b_arg_0_0")]
            else:
                assert "arg_0_0" not in self.matcher_values
                assert "b_arg_0_0" not in self.matcher_values
            self.emit(ir.ExprStmt(ir.Call(ir.Symbol(marker.name), args)))

    builder = MarkerCodegen(ir.Value("self"), ir.Value("op"), {})
    values = {"arg_0": ir.Value("arg_0"), "b_arg_0": ir.Value("b_arg_0")}
    builder.matcher_values = values
    outer_block = builder.block
    builder.visit(OpMatcher(
        "arg_0", "int_neg", Marker("yes"),
        Marker("no") if with_fallbacks else None,
        Marker("next") if with_fallbacks else None, ["arg_0_0"]))
    expected_else = (
        "Block([ExprStmt(Call(Symbol('no'), [], []))])"
        if with_fallbacks else "Block([])")
    expected_next = (
        ", ExprStmt(Call(Symbol('next'), [], []))" if with_fallbacks else "")
    assert repr(builder.block) == (
        "Block([Bind(Value('arg_0_int_neg'), "
        "Call(Attribute(Attribute(Ref(Value('self')), 'optimizer'), 'as_operation'), "
        "[Ref(Value('arg_0')), Attribute(Symbol('rop'), 'INT_NEG')], [])), "
        "If(Binary('is not', Ref(Value('arg_0_int_neg')), Literal(None)), "
        "Block([Bind(Value('arg_0_0'), Call(Symbol('get_box_replacement'), "
        "[Call(Attribute(Ref(Value('arg_0_int_neg')), 'getarg'), [Literal(0)], [])], [])), "
        "Bind(Value('b_arg_0_0'), Call(Attribute(Ref(Value('self')), 'getintbound'), "
        "[Ref(Value('arg_0_0'))], [])), "
        "ExprStmt(Call(Symbol('yes'), "
        "[Ref(Value('arg_0_0')), Ref(Value('b_arg_0_0'))], []))]), "
        "%s)%s])" % (expected_else, expected_next))
    assert builder.block is outer_block
    assert builder.matcher_values is values
    assert "arg_0_0" not in values
    assert "b_arg_0_0" not in values


@pytest.mark.parametrize("name, matcher_name", [("x", "arg_0"), ("C", "C_arg_0")])
def test_ir_pattern_variable_first_occurrence(name, matcher_name):
    from rpython.jit.metainterp.ruleopt import ir

    builder = IRCodegen(ir.Value("self"), ir.Value("op"), {})
    builder.matcher_values[matcher_name] = ir.Value("matched")
    if name == "x":
        builder.matcher_values["b_" + matcher_name] = ir.Value("bound")
    builder.match_variable(PatternVar(name), matcher_name)
    assert repr(builder.bindings[name]) == "Value('matched')"
    if name == "x":
        assert repr(builder.intbound_bindings[name]) == "Value('bound')"
    else:
        assert builder.intbound_bindings == {}
    assert repr(builder.block) == "Block([])"
    # Matching the same Value again should not introduce a condition.
    builder.match_variable(PatternVar(name), matcher_name)
    assert repr(builder.block) == "Block([])"


@pytest.mark.parametrize("name, matcher_name, expected_condition", [
    ("x", "arg_1",
     "Call(Attribute(Ref(Value('self')), '_eq'), "
     "[Ref(Value('second')), Ref(Value('bound_second')), "
     "Ref(Value('first')), Ref(Value('bound_first'))], [])"),
    ("C", "C_arg_1", "Binary('==', Ref(Value('second')), Ref(Value('first')))"),
])
def test_ir_pattern_variable_repeated(name, matcher_name, expected_condition):
    from rpython.jit.metainterp.ruleopt import ir

    builder = IRCodegen(ir.Value("self"), ir.Value("op"),
                        {name: ir.Value("first")},
                        {"x": ir.Value("bound_first")} if name == "x" else {})
    builder.matcher_values[matcher_name] = ir.Value("second")
    if name == "x":
        builder.matcher_values["b_" + matcher_name] = ir.Value("bound_second")
    outer = builder.block
    builder.match_variable(PatternVar(name), matcher_name)
    builder.emit(ir.Return())
    assert repr(outer) == "Block([If(%s, Block([Return(None)]), Block([]))])" % expected_condition
    assert repr(builder.bindings[name]) == "Value('first')"
    if name == "x":
        assert repr(builder.intbound_bindings[name]) == "Value('bound_first')"


def test_ir_terminal_reuses_inner_operation():
    from rpython.jit.metainterp.ruleopt import ir

    rule = parse('''\
and_absorb: int_and(a, int_and(a, b))
    => int_and(a, b)
''').rules[0]
    paths = {
        (('int_and', 0),): 'arg_0',
        (('int_and', 1),): 'arg_1',
        (('int_and', 1), ('int_and', 0)): 'arg_1_0',
        (('int_and', 1), ('int_and', 1)): 'arg_1_1',
    }
    builder = IRCodegen(ir.Value('self'), ir.Value('op'), {})
    builder.method_opname = 'int_and'
    builder.name_positions = {'and_absorb': 0}
    builder.matcher_values = dict((name, ir.Value(name)) for name in (
        'arg_0', 'b_arg_0', 'arg_1', 'b_arg_1',
        'arg_1_0', 'b_arg_1_0', 'arg_1_1', 'b_arg_1_1'))
    builder.visit(Terminal([rule], paths))
    assert repr(builder.block) == (
        "Block([If(Call(Attribute(Ref(Value('self')), '_eq'), "
        "[Ref(Value('arg_1_0')), Ref(Value('b_arg_1_0')), "
        "Ref(Value('arg_0')), Ref(Value('b_arg_0'))], []), "
        "Block([ExprStmt(Call(Attribute(Ref(Value('self')), 'make_equal_to'), "
        "[Ref(Value('op')), Ref(Value('arg_1'))], [])), "
        "FinishRule(Ref(Value('self')), 'int_and', 0, "
        "'and_absorb: int_and(a, int_and(a, b)) => int_and(a, b)')]), "
        "Block([]))])")


def test_ir_terminal_nested_constant_variable():
    from rpython.jit.metainterp.ruleopt import ir

    rule = Rule("cancel", PatternOp("int_sub", [
        PatternOp("int_add", [PatternVar("x"), PatternVar("C")]),
        PatternVar("C"),
    ]), False, [], PatternVar("x", IntBound))
    paths = {
        (("int_sub", 0), ("int_add", 0)): "arg_0_0",
        (("int_sub", 0), ("int_add", 1), "C"): "C_arg_0_1",
        (("int_sub", 1), "C"): "C_arg_1",
    }
    builder = IRCodegen(ir.Value("self"), ir.Value("op"), {})
    builder.method_opname = "int_sub"
    builder.name_positions = {"cancel": 0}
    builder.matcher_values = dict((name, ir.Value(name)) for name in (
        "arg_0_0", "b_arg_0_0", "C_arg_0_1", "C_arg_1"))
    builder.visit(Terminal([rule], paths))
    assert repr(builder.block) == (
        "Block([If(Binary('==', Ref(Value('C_arg_1')), Ref(Value('C_arg_0_1'))), "
        "Block([ExprStmt(Call(Attribute(Ref(Value('self')), 'make_equal_to'), "
        "[Ref(Value('op')), Ref(Value('arg_0_0'))], [])), "
        "FinishRule(Ref(Value('self')), 'int_sub', 0, "
        "'cancel: int_sub(int_add(x, C), C) => x')]), Block([]))])")


def test_ir_terminal_keeps_candidate_conditions_separate():
    from rpython.jit.metainterp.ruleopt import ir

    rules = [
        Rule("and_zero", PatternOp("int_and", [PatternVar("x"), PatternConst("0")]),
             False, [], PatternConst("0")),
        Rule("and_minus_one", PatternOp("int_and", [PatternVar("y"), PatternConst("-1")]),
             False, [], PatternVar("y", IntBound)),
    ]
    paths = {(("int_and", 0),): "arg_0", (("int_and", 1), "C"): "C_arg_1"}
    bindings = {"outer": ir.Value("outer")}
    bounds = {"outer": ir.Value("bound_outer")}
    builder = IRCodegen(ir.Value("self"), ir.Value("op"), bindings, bounds)
    outer = builder.block
    builder.method_opname = "int_and"
    builder.name_positions = {"and_zero": 0, "and_minus_one": 1}
    builder.matcher_values = dict((name, ir.Value(name)) for name in (
        "arg_0", "b_arg_0", "C_arg_1"))
    builder.visit(Terminal(rules, paths))
    assert repr(builder.block) == (
        "Block([If(Binary('==', Ref(Value('C_arg_1')), Literal(0)), "
        "Block([ExprStmt(Call(Attribute(Ref(Value('self')), 'make_constant'), "
        "[Ref(Value('op')), Symbol('CONST_FALSE')], [])), "
        "FinishRule(Ref(Value('self')), 'int_and', 0, "
        "'and_zero: int_and(x, 0) => 0')]), Block([])), "
        "If(Binary('==', Ref(Value('C_arg_1')), Literal(-1)), "
        "Block([ExprStmt(Call(Attribute(Ref(Value('self')), 'make_equal_to'), "
        "[Ref(Value('op')), Ref(Value('arg_0'))], [])), "
        "FinishRule(Ref(Value('self')), 'int_and', 1, "
        "'and_minus_one: int_and(y, -1) => y')]), Block([]))])")
    assert builder.block is outer
    assert builder.bindings is bindings
    assert builder.intbound_bindings is bounds


def test_ir_complete_method():
    from rpython.jit.metainterp.ruleopt import ir

    rule = Rule("sub_same", PatternOp("int_sub", [PatternVar("x"), PatternVar("x")]),
                False, [], PatternConst("0"))
    builder = IRCodegen(ir.Value("self"), ir.Value("op"), {})
    body = builder.generate_method("int_sub", [rule])
    assert body is builder.block
    assert builder.rule_names == ["sub_same"]
    assert builder.name_positions == {"sub_same": 0}
    assert repr(body) == (
        "Block([Bind(Value('arg_0'), Call(Symbol('get_box_replacement'), "
        "[Call(Attribute(Ref(Value('op')), 'getarg'), [Literal(0)], [])], [])), "
        "Bind(Value('b_arg_0'), Call(Attribute(Ref(Value('self')), 'getintbound'), "
        "[Ref(Value('arg_0'))], [])), "
        "Bind(Value('arg_1'), Call(Symbol('get_box_replacement'), "
        "[Call(Attribute(Ref(Value('op')), 'getarg'), [Literal(1)], [])], [])), "
        "Bind(Value('b_arg_1'), Call(Attribute(Ref(Value('self')), 'getintbound'), "
        "[Ref(Value('arg_1'))], [])), "
        "If(Call(Attribute(Ref(Value('self')), '_eq'), "
        "[Ref(Value('arg_1')), Ref(Value('b_arg_1')), "
        "Ref(Value('arg_0')), Ref(Value('b_arg_0'))], []), "
        "Block([ExprStmt(Call(Attribute(Ref(Value('self')), 'make_constant'), "
        "[Ref(Value('op')), Symbol('CONST_FALSE')], [])), "
        "FinishRule(Ref(Value('self')), 'int_sub', 0, "
        "'sub_same: int_sub(x, x) => 0')]), Block([])), "
        "Return(Call(Attribute(Ref(Value('self')), '_emit_generated'), "
        "[Ref(Value('op')), Attribute(Symbol('rop'), 'INT_SUB')], []))])")


def test_ir_method_expands_commutativity_with_shared_counter():
    from rpython.jit.metainterp.ruleopt import ir

    rule = Rule("add_zero", PatternOp("int_add", [PatternVar("x"), PatternConst("0")]),
                False, [], PatternVar("x", IntBound))
    builder = IRCodegen(ir.Value("self"), ir.Value("op"), {})
    body = builder.generate_method("int_add", [rule])
    assert builder.rule_names == ["add_zero"]
    assert builder.name_positions == {"add_zero": 0}
    # Skip the four argument/bound bindings, checked by test_ir_complete_method.
    assert repr(body.statements[4:]) == (
        "[If(Call(Attribute(Ref(Value('b_arg_0')), 'is_constant'), [], []), "
        "Block([Bind(Value('C_arg_0'), "
        "Call(Attribute(Ref(Value('b_arg_0')), 'get_constant_int'), [], [])), "
        "If(Binary('==', Ref(Value('C_arg_0')), Literal(0)), "
        "Block([ExprStmt(Call(Attribute(Ref(Value('self')), 'make_equal_to'), "
        "[Ref(Value('op')), Ref(Value('arg_1'))], [])), "
        "FinishRule(Ref(Value('self')), 'int_add', 0, "
        "'add_zero: int_add(0, x) => x')]), Block([]))]), Block([])), "
        "If(Call(Attribute(Ref(Value('b_arg_1')), 'is_constant'), [], []), "
        "Block([Bind(Value('C_arg_1'), "
        "Call(Attribute(Ref(Value('b_arg_1')), 'get_constant_int'), [], [])), "
        "If(Binary('==', Ref(Value('C_arg_1')), Literal(0)), "
        "Block([ExprStmt(Call(Attribute(Ref(Value('self')), 'make_equal_to'), "
        "[Ref(Value('op')), Ref(Value('arg_0'))], [])), "
        "FinishRule(Ref(Value('self')), 'int_add', 0, "
        "'add_zero: int_add(x, 0) => x')]), Block([]))]), Block([])), "
        "Return(Call(Attribute(Ref(Value('self')), '_emit_generated'), "
        "[Ref(Value('op')), Attribute(Symbol('rop'), 'INT_ADD')], []))]")
