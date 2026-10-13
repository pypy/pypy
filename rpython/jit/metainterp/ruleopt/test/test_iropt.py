import pytest

from rpython.jit.metainterp.ruleopt import ir
from rpython.jit.metainterp.ruleopt.iropt import (
    move_bindings_down, remove_unused_bindings, used_values)


def getintbound(receiver, box):
    return ir.Call(ir.Attribute(ir.Ref(receiver), 'getintbound'), [ir.Ref(box)])


def test_remove_unused_bindings():
    self_value = ir.Value('self')
    box = ir.Value('x')
    block = ir.Block([
        ir.Bind(ir.Value('bound'), getintbound(self_value, box)),
        ir.Return(ir.Ref(box)),
    ])
    remove_unused_bindings(block)
    assert repr(block) == "Block([Return(Ref(Value('x')))])"


def test_nested_uses_and_same_name_hints():
    self_value = ir.Value('self')
    box = ir.Value('x')
    live = ir.Value('bound')
    dead = ir.Value('bound')
    binding = ir.Bind(live, getintbound(self_value, box))
    then_block = ir.Block([
        ir.Bind(dead, getintbound(self_value, box)),
        ir.Return(ir.Ref(live)),
    ])
    else_block = ir.Block([
        ir.Bind(ir.Value('other'), getintbound(self_value, box)),
        ir.Return(),
    ])
    branch = ir.If(ir.Symbol('condition'), then_block, else_block)
    block = ir.Block([binding, branch])
    remove_unused_bindings(block)
    assert block.statements == [binding, branch]
    assert repr(then_block) == "Block([Return(Ref(Value('bound')))])"
    assert then_block.statements[0].expr.value is live
    assert repr(else_block) == 'Block([Return(None)])'


def test_preserve_other_calls_and_argument_effects():
    self_value = ir.Value('self')
    box = ir.Value('x')
    calls = [
        ir.Call(ir.Symbol('side_effect'), [], side_effects=True),
        ir.Call(ir.Attribute(ir.Ref(self_value), 'getintbound'),
                [ir.Call(ir.Symbol('side_effect'), [], side_effects=True)]),
        ir.Call(ir.Attribute(ir.Ref(self_value), 'getintbound'),
                [ir.Ref(box)], [('flag', ir.Call(ir.Symbol('side_effect'), [], side_effects=True))]),
    ]
    statements = [ir.Bind(ir.Value('unused'), call) for call in calls]
    block = ir.Block(statements[:])
    remove_unused_bindings(block)
    assert block.statements == statements


def test_remove_other_unused_bindings():
    calls = ir.Call(ir.Symbol('read'), [ir.Literal(1)], [('flag', ir.Literal(True))])
    action = ir.ExprStmt(ir.Call(ir.Symbol('action'), [], side_effects=True))
    block = ir.Block([
        ir.Bind(ir.Value('constant'), ir.Literal(42)),
        ir.Bind(ir.Value('sum'), ir.Binary('+', ir.Literal(1), ir.Literal(2))),
        ir.Bind(ir.Value('result'), calls),
        action,
    ])
    remove_unused_bindings(block)
    assert block.statements == [action]


def test_remove_dead_chain_across_blocks():
    a, b, c = [ir.Value(name) for name in 'abc']
    then_block = ir.Block([
        ir.Bind(b, ir.Call(ir.Symbol('compute'), [ir.Ref(a)])),
        ir.Bind(c, ir.Ref(b)),
    ])
    branch = ir.If(ir.Symbol('condition'), then_block, ir.Block([]))
    block = ir.Block([
        ir.Bind(a, ir.Call(ir.Symbol('read'), [])),
        branch,
    ])
    remove_unused_bindings(block)
    assert block.statements == [branch]
    assert repr(then_block) == 'Block([])'


def test_repetition_preserves_effectful_chain():
    a, b, dead = [ir.Value(name) for name in ['a', 'b', 'dead']]
    read = ir.Bind(a, ir.Call(ir.Symbol('read'), []))
    effect = ir.Bind(b, ir.Call(ir.Symbol('update'), [ir.Ref(a)],
                                side_effects=True))
    block = ir.Block([read, effect, ir.Bind(dead, ir.Ref(b))])
    remove_unused_bindings(block)
    assert block.statements == [read, effect]


def test_used_values():
    defined = ir.Value('x')
    referenced = ir.Value('x')
    block = ir.Block([
        ir.Bind(defined, ir.Literal(1)),
        ir.If(ir.Symbol('condition'), ir.Block([ir.Return(ir.Ref(referenced))]),
              ir.Block([])),
    ])
    assert used_values(block) == {referenced}


def test_move_bindings_down():
    bound = ir.Value('bound')
    binding = ir.Bind(bound, getintbound(ir.Value('self'), ir.Value('box')))
    early_return = ir.If(ir.Symbol('matched'), ir.Block([ir.Return()]), ir.Block([]))
    ret = ir.Return(ir.Ref(bound))
    block = ir.Block([binding, early_return, ret])
    move_bindings_down(block)
    assert block.statements == [early_return, binding, ret]


@pytest.mark.parametrize('use_in', ['condition', 'then', 'else'])
def test_move_bindings_down_stops_at_use(use_in):
    value = ir.Value('x')
    binding = ir.Bind(value, ir.Literal(1))
    branch = ir.If(ir.Symbol('condition'), ir.Block([]), ir.Block([]))
    if use_in == 'condition':
        branch.condition = ir.Ref(value)
    else:
        arm = branch.then_block if use_in == 'then' else branch.else_block
        arm.statements.append(ir.Return(ir.Ref(value)))
    block = ir.Block([binding, branch])
    move_bindings_down(block)
    assert block.statements == [binding, branch]


def test_move_bindings_down_repeats_inside_nested_blocks():
    a, b = ir.Value('a'), ir.Value('b')
    first = ir.Bind(a, ir.Literal(1))
    second = ir.Bind(b, ir.Ref(a))
    check1 = ir.If(ir.Symbol('first_match'), ir.Block([ir.Return()]), ir.Block([]))
    check2 = ir.If(ir.Symbol('second_match'), ir.Block([ir.Return()]), ir.Block([]))
    ret = ir.Return(ir.Ref(b))
    inner = ir.Block([first, second, check1, check2, ret])
    outer_if = ir.If(ir.Symbol('outer'), ir.Block([]), inner)
    block = ir.Block([outer_if])
    move_bindings_down(block)
    assert block.statements == [outer_if]
    assert inner.statements == [check1, check2, first, second, ret]


def test_move_bindings_down_keeps_effectful_binding():
    binding = ir.Bind(ir.Value('result'),
                      ir.Call(ir.Symbol('update'), [], side_effects=True))
    branch = ir.If(ir.Symbol('condition'), ir.Block([ir.Return()]), ir.Block([]))
    block = ir.Block([binding, branch])
    move_bindings_down(block)
    assert block.statements == [binding, branch]


def test_move_bindings_down_does_not_cross_other_statements():
    binding = ir.Bind(ir.Value('x'), ir.Literal(1))
    action = ir.ExprStmt(ir.Call(ir.Symbol('action'), [], side_effects=True))
    branch = ir.If(ir.Symbol('condition'), ir.Block([ir.Return()]), ir.Block([]))
    block = ir.Block([binding, action, branch])
    move_bindings_down(block)
    assert block.statements == [binding, action, branch]
