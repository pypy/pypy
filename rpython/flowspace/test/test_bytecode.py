"""Unit tests for rpython.flowspace.bytecode"""

from rpython.flowspace.bytecode import bc_reader

def make_graph(func):
    return bc_reader.build_flow(bc_reader.build_code(func.__code__))

def test_graph_dump():
    def f(x):
        if x:
            return 1
        else:
            return 0
    bc_graph = make_graph(f)
    assert [lst[0].offset for lst in bc_graph.dump()] == [0, 6, 10]
    assert bc_graph.dump()[0][0] == bc_reader.new_instr('LOAD_FAST', 0)

def test_blockstack():
    def f():
        for x in lst:
            xxx
    graph = make_graph(f)
    for block in graph.all_blocks():
        if bc_reader.new_instr('LOAD_GLOBAL', 'xxx') in block.operations:
            break
    else:
        assert False
    assert len(block.blockstack) == 1
