import pytest

from rpython.jit.metainterp.ruleopt import ir
from rpython.jit.metainterp.ruleopt.emit import emit_python


def run_body(source):
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
