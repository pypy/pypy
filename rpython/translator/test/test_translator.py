from rpython.translator.translator import TranslationContext, _annotate_blocks_with_source
from rpython.flowspace.model import FunctionGraph, Block, Variable, SpaceOperation


def example(d):
    try:
        d['key']
    except KeyError:
        d['key'] = 'value'

def test_example():
    t = TranslationContext()
    t.buildflowgraph(example)
    # this specific example triggered a bug in simplify.py
    #t.view()


# --- tests for _annotate_blocks_with_source ---

def _make_block_with_op(offset):
    """Return a Block with one dummy SpaceOperation at the given bytecode offset."""
    v = Variable('v')
    result = Variable('result')
    op = SpaceOperation('int_add', [v], result)
    op.offset = offset
    block = Block([v])
    block.operations = [op]
    return block


def test_annotate_blocks_sets_source_func_and_line():
    # Normal case: buildflowgraph annotates all non-empty blocks with
    # source_func (the function object) and a valid source_line integer.
    def f(x):
        return x + 1

    t = TranslationContext()
    graph = t.buildflowgraph(f)

    annotated = [b for b in graph.iterblocks()
                 if getattr(b, 'source_func', None) is not None]
    assert annotated, "at least one block should have source_func set"
    for block in annotated:
        assert block.source_func is f
        assert isinstance(block.source_line, int)
        assert block.source_line > 0


def test_annotate_blocks_skips_graph_without_func():
    # If the graph has no 'func' attribute (e.g. a synthetic graph),
    # _annotate_blocks_with_source must not touch any blocks.
    block = _make_block_with_op(offset=0)
    returnblock = Block([Variable('r')])
    returnblock.operations = ()
    block.closeblock()

    graph = FunctionGraph('synthetic', block, Variable('r'))
    # Deliberately omit graph.func

    _annotate_blocks_with_source(graph)

    assert not hasattr(block, 'source_func')
    assert not hasattr(block, 'source_line')


def test_annotate_blocks_skips_function_without_code():
    # If graph.func has no __code__ (e.g. a built-in), return early.
    block = _make_block_with_op(offset=0)
    returnblock = Block([Variable('r')])
    returnblock.operations = ()
    block.closeblock()

    graph = FunctionGraph('nocode', block, Variable('r'))
    graph.func = len  # built-in: no __code__

    _annotate_blocks_with_source(graph)

    assert not hasattr(block, 'source_func')
    assert not hasattr(block, 'source_line')


def test_annotate_blocks_skips_empty_blocks():
    # Blocks with no operations must not receive source annotations.
    def f(x):
        return x + 1

    t = TranslationContext()
    graph = t.buildflowgraph(f)

    for block in graph.iterblocks():
        if not block.operations:
            assert not hasattr(block, 'source_func')
            assert not hasattr(block, 'source_line')


def test_annotate_blocks_skips_negative_offset():
    # A block whose first operation has a negative offset (synthetic op) must
    # not be annotated, because offset2lineno cannot map it to a source line.
    def f(x):
        return x + 1

    block = _make_block_with_op(offset=-1)
    returnblock = Block([Variable('r')])
    returnblock.operations = ()
    block.closeblock()

    graph = FunctionGraph('negoffset', block, Variable('r'))
    graph.func = f

    _annotate_blocks_with_source(graph)

    assert not hasattr(block, 'source_func')
    assert not hasattr(block, 'source_line')
