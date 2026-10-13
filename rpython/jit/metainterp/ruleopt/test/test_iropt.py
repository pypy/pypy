from rpython.jit.metainterp.ruleopt import ir
from rpython.jit.metainterp.ruleopt.iropt import remove_unused_bindings


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
