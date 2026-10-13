import pytest

from rpython.jit.metainterp.ruleopt import ir
from rpython.jit.metainterp.ruleopt.iropt import (
    move_bindings_down, move_bindings_in, optimize, remove_unused_bindings,
    remove_redundant_guards, same_expression, used_values)


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
    assert move_bindings_down(block) is True
    assert block.statements == [early_return, binding, ret]
    assert move_bindings_down(block) is False


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


@pytest.mark.parametrize('arm_name', ['then_block', 'else_block'])
def test_move_bindings_in(arm_name):
    value = ir.Value('x')
    binding = ir.Bind(value, ir.Call(ir.Symbol('read'), []))
    ret = ir.Return(ir.Ref(value))
    branch = ir.If(ir.Symbol('condition'), ir.Block([]), ir.Block([]))
    arm = getattr(branch, arm_name)
    arm.statements.append(ret)
    block = ir.Block([binding, branch, ir.Return()])
    assert move_bindings_in(block) is True
    assert block.statements[0] is branch
    assert len(block.statements) == 2
    assert arm.statements == [binding, ret]
    assert move_bindings_in(block) is False


@pytest.mark.parametrize('reason', ['condition', 'both_branches', 'later_use',
                                  'unused', 'effectful'])
def test_move_bindings_in_keeps_binding(reason):
    value = ir.Value('x')
    binding = ir.Bind(value, ir.Call(ir.Symbol('read'), [],
                                    side_effects=(reason == 'effectful')))
    branch = ir.If(ir.Symbol('condition'),
                   ir.Block([ir.Return(ir.Ref(value))]), ir.Block([]))
    after = ir.Return()
    if reason == 'condition':
        branch.condition = ir.Ref(value)
    elif reason == 'both_branches':
        branch.else_block.statements.append(ir.Return(ir.Ref(value)))
    elif reason == 'later_use':
        # A use nested inside a later statement must also prevent movement.
        after = ir.If(ir.Symbol('later'), ir.Block([]),
                      ir.Block([ir.Return(ir.Ref(value))]))
    elif reason == 'unused':
        branch.then_block.statements = []
    block = ir.Block([binding, branch, after])
    before = repr(block)
    move_bindings_in(block)
    assert repr(block) == before


def test_move_bindings_in_repeats_and_preserves_dependencies():
    a, b = ir.Value('a'), ir.Value('b')
    first = ir.Bind(a, ir.Call(ir.Symbol('read'), []))
    second = ir.Bind(b, ir.Ref(a))
    ret = ir.Return(ir.Ref(b))
    inner = ir.If(ir.Symbol('inner'), ir.Block([]), ir.Block([ret]))
    outer = ir.If(ir.Symbol('outer'), ir.Block([inner]), ir.Block([]))
    block = ir.Block([first, second, outer])
    move_bindings_in(block)
    assert block.statements == [outer]
    assert outer.then_block.statements == [inner]
    assert inner.else_block.statements == [first, second, ret]


def test_move_bindings_in_does_not_cross_other_statements():
    value = ir.Value('x')
    binding = ir.Bind(value, ir.Literal(1))
    action = ir.ExprStmt(ir.Call(ir.Symbol('action'), [], side_effects=True))
    branch = ir.If(ir.Symbol('condition'),
                   ir.Block([ir.Return(ir.Ref(value))]), ir.Block([]))
    block = ir.Block([binding, action, branch])
    before = repr(block)
    move_bindings_in(block)
    assert repr(block) == before


def test_optimize_alternates_down_and_in():
    value = ir.Value('x')
    binding = ir.Bind(value, ir.Call(ir.Symbol('read'), []))
    ret = ir.Return(ir.Ref(value))
    inner = ir.If(ir.Symbol('inner'), ir.Block([]), ir.Block([ret]))
    early_return = ir.If(ir.Symbol('early'), ir.Block([ir.Return()]), ir.Block([]))
    outer = ir.If(ir.Symbol('outer'), ir.Block([early_return, inner]), ir.Block([]))
    block = ir.Block([binding, outer])

    # First move into outer, then down past early_return, then into inner.
    optimize(block)
    assert block.statements == [outer]
    assert outer.then_block.statements == [early_return, inner]
    assert inner.else_block.statements == [binding, ret]
    before = repr(block)
    optimize(block)
    assert repr(block) == before


@pytest.mark.parametrize('make_expr', [
    lambda v: ir.Ref(v),
    lambda v: ir.Literal(42),
    lambda v: ir.Symbol('external'),
    lambda v: ir.Attribute(ir.Ref(v), 'field'),
    lambda v: ir.Unary('not', ir.Ref(v)),
    lambda v: ir.Binary('==', ir.Ref(v), ir.Literal(0)),
    lambda v: ir.ListExpr([ir.Ref(v), ir.Literal(None)]),
    lambda v: ir.Call(ir.Attribute(ir.Ref(v), 'check'), [ir.Literal(1)],
                      [('flag', ir.Literal(True))]),
])
def test_same_expression(make_expr):
    value = ir.Value('x')
    assert same_expression(make_expr(value), make_expr(value))


def test_same_expression_uses_value_identity():
    first, second = ir.Value('x'), ir.Value('x')
    assert not same_expression(ir.Ref(first), ir.Ref(second))
    assert same_expression(ir.Ref(first), ir.Ref(first))


@pytest.mark.parametrize('left, right', [
    (ir.Literal(0), ir.Literal(False)),
    (ir.Literal(0), ir.Literal(1)),
    (ir.Symbol('x'), ir.Symbol('y')),
    (ir.Symbol('x'), ir.Literal('x')),
    (ir.Attribute(ir.Symbol('x'), 'a'), ir.Attribute(ir.Symbol('x'), 'b')),
    (ir.Unary('-', ir.Literal(1)), ir.Unary('~', ir.Literal(1))),
    (ir.Binary('==', ir.Literal(1), ir.Literal(2)),
     ir.Binary('!=', ir.Literal(1), ir.Literal(2))),
    (ir.ListExpr([ir.Literal(1)]), ir.ListExpr([ir.Literal(1), ir.Literal(2)])),
    (ir.Call(ir.Symbol('f'), [ir.Literal(1), ir.Literal(2)]),
     ir.Call(ir.Symbol('f'), [ir.Literal(2), ir.Literal(1)])),
    (ir.Call(ir.Symbol('f'), [], [('a', ir.Literal(1))]),
     ir.Call(ir.Symbol('f'), [], [('b', ir.Literal(1))])),
    (ir.Call(ir.Symbol('f'), [], [('a', ir.Literal(1)), ('b', ir.Literal(2))]),
     ir.Call(ir.Symbol('f'), [], [('b', ir.Literal(2)), ('a', ir.Literal(1))])),
    (ir.Call(ir.Symbol('f'), []), ir.Call(ir.Symbol('g'), [])),
    (ir.Call(ir.Symbol('f'), []), ir.Call(ir.Symbol('f'), [], side_effects=True)),
])
def test_different_expressions(left, right):
    assert not same_expression(left, right)


@pytest.mark.parametrize('finish_rule', [False, True])
def test_remove_redundant_guards(finish_rule):
    value = ir.Value('x')
    def condition():
        return ir.Call(ir.Symbol('check'), [ir.Ref(value)])
    finish = (ir.FinishRule(ir.Symbol('self'), 'int_eq', 0, 'first')
              if finish_rule else ir.Return())
    first = ir.If(condition(), ir.Block([finish]), ir.Block([]))
    # The targets need not match: the first successful branch already returns.
    second = ir.If(condition(), ir.Block([ir.Return(ir.Literal(2))]), ir.Block([]))
    third = ir.If(condition(), ir.Block([ir.Return(ir.Literal(3))]), ir.Block([]))
    inner = ir.Block([first, second, third])
    outer = ir.If(ir.Symbol('outer'), ir.Block([]), inner)
    block = ir.Block([outer])
    assert remove_redundant_guards(block) is True
    assert block.statements == [outer]
    assert inner.statements == [first]
    assert remove_redundant_guards(block) is False


@pytest.mark.parametrize('reason', [
    'no_return', 'conditional_return', 'first_else', 'second_else',
    'intervening_statement', 'different_value', 'effectful_condition',
])
def test_keep_guards(reason):
    value = ir.Value('x')
    first_condition = ir.Call(ir.Symbol('check'), [ir.Ref(value)],
                              side_effects=(reason == 'effectful_condition'))
    second_value = ir.Value('x') if reason == 'different_value' else value
    second_condition = ir.Call(ir.Symbol('check'), [ir.Ref(second_value)],
                               side_effects=(reason == 'effectful_condition'))
    first = ir.If(first_condition, ir.Block([ir.Return()]), ir.Block([]))
    second = ir.If(second_condition, ir.Block([ir.Return()]), ir.Block([]))
    block = ir.Block([first, second])
    if reason == 'no_return':
        first.then_block.statements = []
    elif reason == 'conditional_return':
        first.then_block.statements = [
            ir.If(ir.Symbol('extra_check'), ir.Block([ir.Return()]), ir.Block([]))]
    elif reason == 'first_else':
        first.else_block.statements = [ir.ExprStmt(ir.Call(
            ir.Symbol('update'), [], side_effects=True))]
    elif reason == 'second_else':
        second.else_block.statements = [ir.Return(ir.Literal(1))]
    elif reason == 'intervening_statement':
        block.statements.insert(1, ir.ExprStmt(ir.Call(
            ir.Symbol('update'), [], side_effects=True)))
    before = repr(block)
    assert remove_redundant_guards(block) is False
    assert repr(block) == before


def test_optimize_cleans_up_after_removing_guard():
    unused = ir.Value('only_used_by_second_guard')
    first = ir.If(ir.Symbol('condition'), ir.Block([ir.Return()]), ir.Block([]))
    second = ir.If(ir.Symbol('condition'),
                   ir.Block([ir.Return(ir.Ref(unused))]), ir.Block([]))
    block = ir.Block([ir.Bind(unused, ir.Call(ir.Symbol('read'), [])), first, second])
    optimize(block)
    assert block.statements == [first]
