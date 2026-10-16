import pytest

from rpython.jit.metainterp.ruleopt import ir


@pytest.mark.parametrize('kind', [
    'value', 'ref', 'literal', 'symbol', 'attribute', 'call', 'list',
    'unary', 'binary', 'bind', 'exprstmt', 'return', 'bare_return',
    'finish', 'if', 'block', 'empty_block',
])
def test_iter_children(kind):
    a, b, c, d = [ir.Symbol(name) for name in 'abcd']
    value = ir.Value('x')
    then_block = ir.Block([ir.Return(b)])
    else_block = ir.Block([ir.Return(c)])
    node, expected = {
        'value': (value, []),
        'ref': (ir.Ref(value), []),
        'literal': (ir.Literal(42), []),
        'symbol': (a, []),
        'attribute': (ir.Attribute(a, 'attr'), [a]),
        'call': (ir.Call(a, [b], [('second', c), ('first', d)]), [a, b, c, d]),
        'list': (ir.ListExpr([a, b]), [a, b]),
        'unary': (ir.Unary('-', a), [a]),
        'binary': (ir.Binary('+', a, b), [a, b]),
        'bind': (ir.Bind(value, a), [a]),
        'exprstmt': (ir.ExprStmt(a), [a]),
        'return': (ir.Return(a), [a]),
        'bare_return': (ir.Return(), []),
        'finish': (ir.FinishRule(a, 'int_add', 0, 'rule'), [a]),
        'if': (ir.If(a, then_block, else_block), [a, then_block, else_block]),
        'block': (ir.Block([then_block.statements[0], else_block.statements[0]]),
                  [then_block.statements[0], else_block.statements[0]]),
        'empty_block': (ir.Block([]), []),
    }[kind]
    assert list(node.iter_children()) == expected


def test_walk_preorder():
    value = ir.Value('x')
    literal = ir.Literal(1)
    binding = ir.Bind(value, literal)
    condition = ir.Ref(value)
    result = ir.Ref(value)
    ret = ir.Return(result)
    then_block = ir.Block([ret])
    else_block = ir.Block([])
    branch = ir.If(condition, then_block, else_block)
    block = ir.Block([binding, branch])
    assert list(block.walk()) == [
        block, binding, literal, branch, condition, then_block, ret, result,
        else_block,
    ]


def test_walk_shared_expression_visits_each_occurrence():
    ref = ir.Ref(ir.Value('x'))
    expr = ir.Binary('+', ref, ref)
    assert list(expr.walk()) == [expr, ref, ref]
