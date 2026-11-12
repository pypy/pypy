from rpython.jit.metainterp.ruleopt import ir


def test_shared_values_and_statement_order():
    first = ir.Value('x')
    second = ir.Value('x')
    block = ir.Block([
        ir.Bind(first, ir.Literal(1)),
        ir.Bind(second, ir.Ref(first)),
        ir.Return(ir.Ref(second)),
    ])
    dot = block.as_dot()
    assert dot == block.as_dot()
    assert dot.count('label="Value\\nx"') == 1
    assert dot.count('label="Value\\nx_v1"') == 1
    for index in range(3):
        assert 'label="statements[%s]"' % index in dot
    # Both the binding and the reference point to the same Value node.
    value_line = next(line for line in dot.splitlines()
                      if 'label="Value\\nx"' in line)
    value_id = value_line.strip().split()[0]
    assert dot.count('-> %s [' % value_id) == 2


def test_branches_keywords_and_empty_blocks():
    node = ir.If(
        ir.Call(ir.Symbol('check'), [], [('flag', ir.Literal(True))]),
        ir.Block([ir.FinishRule(ir.Ref(ir.Value('self')), 'int_add',
                                0, 'add_zero')]),
        ir.Block([]))
    dot = node.as_dot()
    for label in ['condition', 'then_block', 'else_block', 'keyword flag']:
        assert 'label="%s"' % label in dot
    assert 'FinishRule' in dot
    assert 'add_zero' in dot
    assert 'statements = []' in dot


def test_escaping():
    dot = ir.FinishRule(ir.Symbol('self'), 'int_add', 0,
                        'a "quote" and \\N\nsecond line').as_dot()
    assert r'\"quote\"' in dot
    assert r'\\N' in dot
    assert r'\nsecond line' in dot


def test_view(monkeypatch):
    from dotviewer.graphpage import GraphPage
    pages = []
    monkeypatch.setattr(GraphPage, 'display', lambda page: pages.append(page))
    # Every kind of IR node can be inspected on its own.
    for node in [ir.Value('x'), ir.Literal(1), ir.Return(), ir.Block([])]:
        node.view()
        assert pages[-1].source == node.as_dot()
        assert pages[-1].links == {}
