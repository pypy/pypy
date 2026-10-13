import pytest

from rpython.jit.metainterp.ruleopt import ir
from rpython.jit.metainterp.ruleopt.emit import emit_python


def run_body(source, namespace=None):
    if namespace is None:
        namespace = {}
    function = "def generated():\n" + "\n".join(
        "    " + line for line in source.splitlines())
    exec(function, namespace)
    return namespace["generated"]()


def test_binding_and_return():
    result = ir.Value("result")
    source = emit_python(ir.Block([
        ir.Bind(result, ir.Literal(42)),
        ir.Return(ir.Ref(result)),
    ]))
    assert source == "result = 42\nreturn result"
    assert run_body(source) == 42


def test_distinct_bindings_with_same_hint():
    first = ir.Value("x")
    second = ir.Value("x")
    source = emit_python(ir.Block([
        ir.Bind(first, ir.Literal(10)),
        ir.Bind(second, ir.Literal(20)),
        ir.Return(ir.Ref(first)),
    ]))
    assert source == "x = 10\nx_1 = 20\nreturn x"
    assert run_body(source) == 10


def test_bare_return_and_explicit_none():
    bare = emit_python(ir.Block([ir.Return()]))
    explicit = emit_python(ir.Block([ir.Return(ir.Literal(None))]))
    assert bare == "return"
    assert explicit == "return None"
    assert run_body(bare) is None
    assert run_body(explicit) is None


@pytest.mark.parametrize("outer, inner, expected", [
    (True, True, 10),
    (True, False, 20),
    (False, True, 30),
])
def test_nested_if(outer, inner, expected):
    body = ir.Block([
        ir.If(ir.Literal(outer), ir.Block([
            ir.If(ir.Literal(inner),
                  ir.Block([ir.Return(ir.Literal(10))]),
                  ir.Block([ir.Return(ir.Literal(20))])),
        ]), ir.Block([])),
        ir.Return(ir.Literal(30)),
    ])
    source = emit_python(body)
    assert source == (
        "if %r:\n"
        "    if %r:\n"
        "        return 10\n"
        "    else:\n"
        "        return 20\n"
        "return 30" % (outer, inner))
    assert run_body(source) == expected


def test_empty_then_block():
    source = emit_python(ir.Block([
        ir.If(ir.Literal(True), ir.Block([]),
              ir.Block([ir.Return(ir.Literal(10))])),
        ir.Return(ir.Literal(20)),
    ]))
    assert source == "if True:\n    pass\nelse:\n    return 10\nreturn 20"
    assert run_body(source) == 20


def test_empty_body():
    source = emit_python(ir.Block([]))
    assert source == "pass"
    assert run_body(source) is None


def test_call_without_arguments():
    expr = ir.Call(ir.Attribute(ir.Literal("hello"), "upper"), [])
    source = emit_python(ir.Block([ir.Return(expr)]))
    assert source == "return ('hello').upper()"
    assert run_body(source) == "HELLO"


def test_nested_calls():
    stripped = ir.Call(ir.Attribute(ir.Literal(" a,b "), "strip"), [])
    split = ir.Call(ir.Attribute(stripped, "split"), [ir.Literal(",")])
    source = emit_python(ir.Block([ir.Return(split)]))
    assert source == "return ((' a,b ').strip()).split(',')"
    assert run_body(source) == ["a", "b"]


def test_call_with_positional_and_keyword_arguments():
    template = ir.Value("template")
    expr = ir.Call(
        ir.Attribute(ir.Ref(template), "format"),
        [ir.Literal("hello")],
        [("suffix", ir.Literal("world"))],
    )
    source = emit_python(ir.Block([
        ir.Bind(template, ir.Literal("{0} {suffix}")),
        ir.Return(expr),
    ]))
    assert source == (
        "template = '{0} {suffix}'\n"
        "return (template).format('hello', suffix='world')")
    assert run_body(source) == "hello world"


@pytest.mark.parametrize("expr, expected_source, expected_result", [
    (ir.Binary("-", ir.Literal(10),
               ir.Binary("-", ir.Literal(3), ir.Literal(1))),
     "return 10 - (3 - 1)", 8),
    (ir.Binary("-", ir.Binary("-", ir.Literal(10), ir.Literal(3)),
               ir.Literal(1)),
     "return 10 - 3 - 1", 6),
    # Parentheses must also prevent Python's chained-comparison semantics.
    (ir.Binary("==", ir.Binary("<", ir.Literal(3), ir.Literal(2)),
               ir.Literal(False)),
     "return (3 < 2) == False", True),
    (ir.Unary("-", ir.Binary("+", ir.Literal(2), ir.Literal(3))),
     "return -(2 + 3)", -5),
    (ir.Unary("not", ir.Literal(False)), "return not False", True),
    (ir.Binary("is", ir.Literal(None), ir.Literal(None)),
     "return None is None", True),
])
def test_operators_preserve_grouping(expr, expected_source, expected_result):
    source = emit_python(ir.Block([ir.Return(expr)]))
    assert source == expected_source
    assert run_body(source) == expected_result


def test_list_of_expressions():
    x = ir.Value("x")
    source = emit_python(ir.Block([
        ir.Bind(x, ir.Literal(4)),
        ir.Return(ir.ListExpr([
            ir.Ref(x), ir.Binary("+", ir.Ref(x), ir.Literal(1)),
        ])),
    ]))
    assert source == "x = 4\nreturn [x, x + 1]"
    assert run_body(source) == [4, 5]


def test_expr_stmt_preserves_effects_and_continues():
    items = ir.Value("items")
    source = emit_python(ir.Block([
        ir.Bind(items, ir.ListExpr([])),
        ir.ExprStmt(ir.Call(ir.Attribute(ir.Ref(items), "append"),
                      [ir.Literal(1)])),
        ir.ExprStmt(ir.Call(ir.Attribute(ir.Ref(items), "append"),
                      [ir.Literal(2)])),
        ir.Return(ir.Ref(items)),
    ]))
    assert source == (
        "items = []\n"
        "(items).append(1)\n"
        "(items).append(2)\n"
        "return items")
    assert run_body(source) == [1, 2]


def test_symbol_call():
    source = emit_python(ir.Block([
        ir.Return(ir.Call(ir.Symbol("len"), [ir.ListExpr([])])),
    ]))
    assert source == "return len([])"
    assert run_body(source) == 0


def test_local_binding_does_not_shadow_symbol():
    local = ir.Value("len")
    source = emit_python(ir.Block([
        ir.Bind(local, ir.Literal(10)),
        ir.Return(ir.Binary("+", ir.Ref(local),
                            ir.Call(ir.Symbol("len"), [ir.ListExpr([])]))),
    ]))
    assert source == "len_1 = 10\nreturn len_1 + len([])"
    assert run_body(source) == 10


@pytest.mark.parametrize("condition", [True, False])
def test_finish_rule_counts_and_returns_only_on_success(condition):
    class Recorder(object):
        def __init__(self):
            self._rule_fired_int_add = [0, 0]

    recorder = Recorder()
    source = emit_python(ir.Block([
        ir.If(ir.Literal(condition), ir.Block([
            ir.FinishRule(ir.Symbol("optimizer"), "int_add", 1,
                          "add_zero: int_add(x, 0) => x"),
        ]), ir.Block([])),
        ir.Return(ir.Literal(42)),
    ]))
    assert source == (
        "if %r:\n"
        "    # add_zero: int_add(x, 0) => x\n"
        "    optimizer._rule_fired_int_add[1] += 1\n"
        "    return\n"
        "return 42" % condition)
    assert run_body(source, {"optimizer": recorder}) == (None if condition else 42)
    assert recorder._rule_fired_int_add == [0, int(condition)]
