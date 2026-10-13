import pytest

from rpython.jit.metainterp.ruleopt import ir


def test_binding_and_reference():
    # Represents: result = 42; return result.
    result = ir.Value("result")
    constant = ir.Literal(42)
    body = ir.Block([
        ir.Bind(result, constant),
        ir.Return(ir.Ref(result)),
    ])

    binding, ret = body.statements
    assert isinstance(binding, ir.Stmt)
    assert isinstance(ret, ir.Stmt)
    assert binding.value is result
    assert binding.expr is constant
    assert binding.expr.value == 42
    assert isinstance(ret.expr, ir.Expr)
    assert ret.expr.value is binding.value
    assert result.name_hint == "result"


def test_name_hint_does_not_identify_a_binding():
    # Separate branches may reuse a printed name for different bindings.
    first = ir.Value("arg_0")
    second = ir.Value("arg_0")
    assert first != second
    assert len({first: 1, second: 2}) == 2
    assert ir.Ref(first).value is first
    assert ir.Ref(second).value is second


@pytest.mark.parametrize("node, expected", [
    (ir.Value("x"), "Value('x')"),
    (ir.Expr(), "Expr()"),
    (ir.Stmt(), "Stmt()"),
    (ir.Ref(ir.Value("x")), "Ref(Value('x'))"),
    (ir.Literal(42), "Literal(42)"),
    (ir.Literal("x"), "Literal('x')"),
    (ir.Unary("-", ir.Literal(1)), "Unary('-', Literal(1))"),
    (ir.Binary("+", ir.Literal(1), ir.Literal(2)),
     "Binary('+', Literal(1), Literal(2))"),
    (ir.Attribute(ir.Ref(ir.Value("b")), "is_constant"),
     "Attribute(Ref(Value('b')), 'is_constant')"),
    (ir.Call(ir.Ref(ir.Value("f")), [ir.Literal(1)],
             [("flag", ir.Literal(True))]),
     "Call(Ref(Value('f')), [Literal(1)], [('flag', Literal(True))])"),
    (ir.Bind(ir.Value("x"), ir.Literal(42)),
     "Bind(Value('x'), Literal(42))"),
    (ir.Return(), "Return(None)"),
    (ir.Return(ir.Ref(ir.Value("x"))), "Return(Ref(Value('x')))"),
    (ir.Block([]), "Block([])"),
    (ir.If(ir.Literal(True), ir.Block([]), ir.Block([])),
     "If(Literal(True), Block([]), Block([]))"),
    (ir.Block([ir.Bind(ir.Value("x"), ir.Literal(42)), ir.Return()]),
     "Block([Bind(Value('x'), Literal(42)), Return(None)])"),
])
def test_repr(node, expected):
    assert repr(node) == expected
